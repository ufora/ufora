#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Core implementation of the SubscribableWebObjects backend."""

import json
import logging
import threading
import traceback


import ufora.FORA.python.ModuleImporter as ModuleImporter

import ufora.BackendGateway.Computations as Computations
import ufora.BackendGateway.ObjectConverter as ObjectConverter
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph

import ufora.BackendGateway.SubscribableWebObjects.AllObjectClassesToExpose \
    as AllObjectClassesToExpose
import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions
import ufora.BackendGateway.SubscribableWebObjects.SubscribableObject as SubscribableObject
import ufora.BackendGateway.SubscribableWebObjects.Subscriptions as Subscriptions

import ufora.util.Unicode as Unicode

import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.FORA as Fora
import ufora.FORA.python.ForaValue as ForaValue

import uuid

class MalformedMessageException(Exception):
    pass

class InvalidObjectDefinitionException(MalformedMessageException):
    pass

class InvalidFieldException(Exceptions.SubscribableWebObjectsException):
    def __init__(self):
        Exceptions.SubscribableWebObjectsException.__init__(self, "Invalid field.")

class InvalidFunctionException(Exceptions.SubscribableWebObjectsException):
    def __init__(self):
        Exceptions.SubscribableWebObjectsException.__init__(self, "Invalid function.")


def getObjectClass(o):
    if ComputedGraph.isLocation(o):
        return ComputedGraph.getLocationTypeFromLocation(o)
    return o.__class__



def calculateLineAndColumn(message, index):
    lineNo = 1
    for line in message.split('\n'):
        if index < len(line):
            return lineNo, index + 1
        lineNo += 1
        index -= len(line) + 1


def unexpectedExceptionJson(jsonMessage, message):
    return {
        "messageId": jsonMessage["messageId"],
        "responseType": "Exception",
        "message": message
        }


class OutgoingObjectCache(object):
    def __init__(self):
        self.objectIdCache_ = {}
        self.objectToIdCache_ = {}
        self.curObjectId = 0
        self.maxObjectIdsToKeep = 10000
        self.minObjectId = 0

    def lookupObjectId(self, obj):
        if obj not in self.objectToIdCache_:
            id = self.newId()

            self.objectToIdCache_[obj] = id
            self.objectIdCache_[id] = obj

        return self.objectToIdCache_[obj]

    def newId(self):
        self.curObjectId += 1
        return self.curObjectId - 1

    def convertResponseToJson(self, jsonCandidate):
        try:
            def raiseException():
                guid = uuid.uuid4()

                logging.error(
                    "%s of type %s is not valid json. guid = %s",
                    jsonCandidate,
                    type(jsonCandidate),
                    guid
                    )
                raise Exceptions.SubscribableWebObjectsException(
                    "result was not valid json. Guid = %s" % guid
                    )

            if jsonCandidate is None:
                return jsonCandidate

            if isinstance(jsonCandidate, (int, str, unicode, float, bool, long)):
                return jsonCandidate

            if isinstance(jsonCandidate, (list, tuple)):
                return [self.convertResponseToJson(r) for r in jsonCandidate]

            if isinstance(jsonCandidate, dict):
                newDict = {}
                for k, v in jsonCandidate.iteritems():
                    if not isinstance(k, str):
                        raiseException()
                    newDict[k] = self.convertResponseToJson(v)

                return newDict

            objDefPopulated = False
            try:
                if ComputedGraph.isLocation(jsonCandidate):
                    if jsonCandidate in self.objectToIdCache_:
                        objDef = {
                            'objectId_': self.lookupObjectId(jsonCandidate)
                            }
                    else:
                        objDef = {
                            "objectId_": self.lookupObjectId(jsonCandidate),
                            "objectDefinition_": {
                                'type': AllObjectClassesToExpose.typenameFromType(
                                    ComputedGraph.getLocationTypeFromLocation(jsonCandidate)
                                    ),
                                'args': jsonCandidate.__reduce__()[1][0]
                                }
                            }
                    objDefPopulated = True
                else:
                    objDef = jsonCandidate.objectDefinition_
                    objDefPopulated = True
            except AttributeError:
                objDefPopulated = False

            if objDefPopulated:
                return self.convertResponseToJson(objDef)

            raiseException()
        except:
            logging.error("%s of type %s is not valid json.", jsonCandidate, type(jsonCandidate))
            raise

    def tryFlushObjectIdCache(self):
        """If we need to flush the objectID cache, do it and return the minimumId to keep. Otherwise None"""
        if self.curObjectId > self.minObjectId + self.maxObjectIdsToKeep:
            newMinId = self.curObjectId

            self.minObjectId = newMinId
            self.objectIdCache_ = {}
            self.objectToIdCache_ = {}

            return newMinId

        return None


class MessageProcessor(object):
    '''
    Message processor for a single SubscribableWebObjects session.
    '''
    # Must be locked before use except where noted
    def __init__(self, cumulus_gateway, cache_loader):
        self.cumulus_gateway = cumulus_gateway
        self.cache_loader = cache_loader
        self.object_converter = ObjectConverter.ObjectConverter(cache_loader.vdm)
        self.computations = Computations.Computations(cumulus_gateway,
                                                      cache_loader.vdm,
                                                      self.object_converter)

        self.lock = threading.Lock()
        self.cacheLoadEvents = {}

        self.resultsById_ = {}
        self.eventsById_ = {}
        self.active_objects = {}

        Runtime.initialize()
        logging.info("Runtime initialized")

        ModuleImporter.initialize()
        logging.info("Module importer initialized")

        Fora._builtin = ForaValue.FORAValue(ModuleImporter.builtinModuleImplVal())

        self.outgoingObjectCache = OutgoingObjectCache()

        #self.VDM = VectorDataManager.constructVDM(callbackScheduler)
        #self.VDM.setDropUnreferencedPagesWhenFull(True)
        #logging.info("created a VDM")

        #with self.graph:
            #self.computedValueGateway = computedValueGatewayFactory()
            #self.cumulusGatewayRemote = self.computedValueGateway.cumulusGateway


        self.outstandingMessagesById = {}
        self.expectedMessageId = 0

        self.messageTypeHandlers = {}

        self.messageTypeHandlers["Read"] = self.handleReadMessage
        self.messageTypeHandlers["Subscribe"] = self.handleSubscribeMessage
        self.messageTypeHandlers["Execute"] = self.handleExecuteMessage
        self.messageTypeHandlers["ServerFlushObjectIdsBelow"] = self.handleFlushObjectIds

        self.pendingObjectQueue = []

        self.subscriptions = Subscriptions.Subscriptions()


    def handleIncomingMessage(self, message):
        responses = []
        try:
            if message:
                jsonMessage = json.loads(message, object_hook=Unicode.convertToStringRecursively)
                responses = self.handleJsonMessage(jsonMessage)
                responses += self.tryFlushObjectIdCache()
            else:
                responses = self.getPendingMessages()

        except UnicodeEncodeError as err:
            self.expectedMessageId += 1
            jsonRequest = json.loads(message)
            line, column = calculateLineAndColumn(err.object, err.start)

            what = {
                'line' : line,
                'column' : column,
                'char' : err.object[err.start : err.end]
            }
            responses = [unexpectedExceptionJson(jsonRequest, what)]
        return responses


    def handleJsonMessage(self, incomingJsonMessage):
        if not isinstance(incomingJsonMessage, dict):
            raise MalformedMessageException(
                "Incoming message was not a dictionary: %s" % incomingJsonMessage)

        if not 'messageId' in incomingJsonMessage:
            raise MalformedMessageException(
                "Invalid incoming message id: %s" % incomingJsonMessage)

        if incomingJsonMessage['messageId'] != self.expectedMessageId:
            raise MalformedMessageException(
                "Invalid incoming message id: expected %s, but got %s. %s" %
                (self.expectedMessageId, incomingJsonMessage['messageId'], incomingJsonMessage)
                )

        try:
            self.expectedMessageId += 1

            if incomingJsonMessage['messageType'] not in self.messageTypeHandlers:
                raise MalformedMessageException("Invalid incoming messageType")

            if not 'objectDefinition' in incomingJsonMessage:
                raise MalformedMessageException("No object definition given")

            obj = None
            if incomingJsonMessage["messageType"] != "ServerFlushObjectIdsBelow":
                obj = self.extractObjectDefinition(incomingJsonMessage['objectDefinition'],
                                                   incomingJsonMessage.get("objectId_"))

            return self.messageTypeHandlers[incomingJsonMessage["messageType"]](incomingJsonMessage,
                                                                                obj)
        except MalformedMessageException:
            raise
        except Exception as e:
            return [unexpectedExceptionJson(incomingJsonMessage,
                                            Exceptions.wrapException(e).message)]

    def tryFlushObjectIdCache(self):
        objectId = self.outgoingObjectCache.tryFlushObjectIdCache()
        if objectId is not None:
            return [{'responseType': 'ClientFlushObjectIdsBelow', 'value':objectId}]
        return []


    def flushIdsBelow(self, threshold):
        object_ids = sorted(self.active_objects.keys())

        while object_ids and object_ids[0] < threshold:
            del self.active_objects[object_ids[0]]
            self.subscriptions.removeAllSubscriptionsForObject(object_ids[0])
            object_ids.pop(0)


    def handleFlushObjectIds(self, incomingJsonMessage, obj):
        if not 'value' in incomingJsonMessage:
            raise MalformedMessageException("missing 'value'")

        threshold = incomingJsonMessage['value']

        if not isinstance(threshold, int):
            raise MalformedMessageException("threshold should be an integer")

        self.flushIdsBelow(threshold)

        return [{
            "messageId": incomingJsonMessage["messageId"],
            "responseType": "OK"
            }]

    def extractObjectDefinition(self, objDefJson, objectId=None):
        if 'objectId_' in objDefJson or 'objectDefinition_' in objDefJson:
            return self.convertObjectArgs(objDefJson)

        if 'type' not in objDefJson or 'args' not in objDefJson:
            raise MalformedMessageException("Malformed object definition given")

        objType = objDefJson['type']
        objectArgs = objDefJson['args']

        objectArgs = self.convertObjectArgs(objectArgs)

        if objType not in AllObjectClassesToExpose.classMap:
            raise InvalidObjectDefinitionException("Unknown object type: %s" % objType)

        try:
            objectCls = AllObjectClassesToExpose.classMap[objType]
            result = objectCls(objectId if objectId is not None else uuid.uuid4().hex,
                               SubscribableObject.CumulusEnvironment(
                                   self.cumulus_gateway,
                                   self.cache_loader,
                                   self.computations,
                                   self.object_converter
                                   ),
                               objectArgs)
            result.__dict__['objectDefinition_'] = objDefJson
            self.active_objects[result.id] = result

            return result
        except Exceptions.SubscribableWebObjectsException as e:
            raise InvalidObjectDefinitionException(e.message)

    def convertObjectArgs(self, objectArgs):
        if isinstance(objectArgs, list):
            return [self.convertObjectArgs(x) for x in objectArgs]

        if isinstance(objectArgs, dict):
            if 'objectDefinition_' in objectArgs:
                return self.extractObjectDefinition(objectArgs['objectDefinition_'],
                                                    objectArgs.get('objectId_'))

            if 'objectId_' in objectArgs:
                obj_id = objectArgs['objectId_']
                obj = self.active_objects.get(obj_id)
                if obj is None:
                    raise MalformedMessageException("Object with ID %s unknown" % obj_id)
                return obj

            tr = {}
            for k, v in objectArgs.iteritems():
                tr[k] = self.convertObjectArgs(v)

            return tr

        return objectArgs

    def getFieldExtractorForReadMessage(self, jsonMessage, objectToRead):
        if 'field' not in jsonMessage:
            raise MalformedMessageException("missing 'field'")

        field = jsonMessage['field']

        if not isinstance(field, str):
            raise MalformedMessageException("fieldname not a string")

        field = intern(field)

        try:
            fieldDef = getattr(getObjectClass(objectToRead), field)
        except:
            raise InvalidFieldException()

        if not SubscribableObject.isPropertyToExpose(fieldDef):
            raise InvalidFieldException()

        def getter(x):
            return getattr(x, field)
        return getter

    def getFunctionForExecuteMessage(self, jsonMessage, objectToRead):
        if 'field' not in jsonMessage:
            raise MalformedMessageException("missing 'field'")

        field = jsonMessage['field']

        if not isinstance(field, str):
            raise MalformedMessageException("fieldname was not a string")

        field = intern(field)

        try:
            funDef = getattr(objectToRead.__class__, field)
        except:
            raise InvalidFieldException()


        if not SubscribableObject.isFunctionToExpose(funDef):
            raise InvalidFunctionException()


        if SubscribableObject.functionExpectsExpandedArgs(funDef):
            def caller(x, callback, arg):
                try:
                    if isinstance(arg, list):
                        callback(getattr(x, field)(*arg))
                    else:
                        callback(getattr(x, field)(**arg))
                except Exception as e:
                    callback(e)

            return caller
        else:
            def caller(x, callback, *args):
                try:
                    callback(getattr(x, field)(*args))
                except Exception as e:
                    callback(e)
            return caller

    def addResultToQueue(self, messageCreator):
        self.pendingObjectQueue.append(messageCreator)

    def handleExecuteMessage(self, jsonMessage, objectToExecuteOn):
        funImplementation = self.getFunctionForExecuteMessage(jsonMessage, objectToExecuteOn)

        def callback(result):
            if isinstance(result, Exception):
                def creator():
                    return unexpectedExceptionJson(jsonMessage,
                                                   Exceptions.wrapException(result).message)
                self.addResultToQueue(creator)
            else:
                def creator():
                    try:
                        return {
                            "messageId": jsonMessage["messageId"],
                            "responseType": "ExecutionResult",
                            "result": self.outgoingObjectCache.convertResponseToJson(result)
                            }
                    except Exception as e:
                        return unexpectedExceptionJson(jsonMessage,
                                                       Exceptions.wrapException(e).message)
                self.addResultToQueue(creator)

        try:
            objectArgs = self.convertObjectArgs(jsonMessage['args'])
            funImplementation(objectToExecuteOn, callback, objectArgs)
            return []
        except Exception as e:
            return [unexpectedExceptionJson(jsonMessage, Exceptions.wrapException(e).message)]



    def handleReadMessage(self, jsonMessage, objectToRead):
        fieldFun = self.getFieldExtractorForReadMessage(jsonMessage, objectToRead)
        try:
            return [{
                "messageId": jsonMessage["messageId"],
                "responseType": "ReadResponse",
                "value": self.outgoingObjectCache.convertResponseToJson(fieldFun(objectToRead))
                }]

        except Exception as e:
            try:
                objectType = (objectToRead.__location_class__
                              if ComputedGraph.isLocation(objectToRead)
                              else str(objectToRead))
                logging.info("converting %s of type %s", fieldFun(objectToRead), objectType)
            except:
                pass
            return [unexpectedExceptionJson(jsonMessage, Exceptions.wrapException(e).message)]


    def handleSubscribeMessage(self, jsonMessage, objectToRead):
        fieldFun = self.getFieldExtractorForReadMessage(jsonMessage, objectToRead)
        value = fieldFun(objectToRead)

        otherSubscriptionChanges = self.subscriptions.addSubscription(
            jsonMessage['messageId'],
            objectToRead,
            jsonMessage['field']
            )

        if isinstance(value, Exceptions.SubscribableWebObjectsException):
            valueResponseJson = unexpectedExceptionJson(jsonMessage, value.message)
        else:
            valueResponseJson = {
                "messageId": jsonMessage["messageId"],
                "responseType": "SubscribeResponse",
                "value": self.outgoingObjectCache.convertResponseToJson(fieldFun(objectToRead))
                }

        return [valueResponseJson] + self.getPendingMessages()


    def encodeSubscriptionChangesAsJsonAndDrop(self, changedSubscriptionIds):
        result = []

        for messageId in changedSubscriptionIds:
            value = self.subscriptions.getValueAndDropSubscription(messageId)

            try:
                if isinstance(value, Exceptions.SubscribableWebObjectsException):
                    valueResponseJson = {
                        "messageId": messageId,
                        "responseType": "Exception",
                        "message": value.message
                        }
                else:
                    valueResponseJson = {
                        "messageId": messageId,
                        "responseType": "ValueChanged",
                        "value": self.outgoingObjectCache.convertResponseToJson(value)
                        }
            except:
                guid = uuid.uuid4()
                logging.error(
                    "Exception occurred converting subscription value to json. guid = %s. tb =\n%s",
                    guid,
                    traceback.format_exc()
                    )

                valueResponseJson = {
                    "messageId": messageId,
                    "responseType": "Exception",
                    "message": "Error converting result to json. guid = %s" % guid
                    }

            result.append(valueResponseJson)

        return result


    def getPendingMessages(self):
        changed = self.subscriptions.updateAndReturnChangedSubscriptionIds()
        return self.encodeSubscriptionChangesAsJsonAndDrop(changed)


    def extractPendingMessages(self):
        tr = [x() for x in self.pendingObjectQueue]
        self.pendingObjectQueue = []
        return tr


    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, type, value, tb):
        self.lock.__exit__(type, value, tb)

    def teardown(self):
        pass
        #self.computedValueGateway = None

