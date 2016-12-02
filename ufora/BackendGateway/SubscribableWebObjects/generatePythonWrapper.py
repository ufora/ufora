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

import ufora.BackendGateway.SubscribableWebObjects.SubscribableObject as SubscribableObject
import cStringIO as StringIO

def addSpaces(lineWriter):
    return lambda s: lineWriter("    " + s)

def getClassMember(cls):
    if cls is object:
        return {}

    prior = {}

    for c in reversed(cls.mro()):
        if c is not object:
            for x, val in c.__dict__.iteritems():
                prior[x] = val

    return prior

headerText = """
"NOTE: THIS IS GENERATED CODE. DO NOT EDIT THIS FILE OR CHECK IT INTO SOURCE CONTROL!"

import json

class WebObjectBase(object):
    def __init__(self, sessionState, inArgs=None):
        self.objectId_ = None
        self.sessionState = sessionState
        self.objectDefinition_ = {
            "args": inArgs if inArgs is not None else {}
        }

    def __str__(self):
        return "%s(objectId: %s, args: %s)" % (type(self),
                                               self.objectId_,
                                               self.objectDefinition_['args'])

    def toJSONWireFormat(self):
        self.sessionState.isConvertingToWireFormat = True
        memoizedJson = self.toMemoizedJSON()
        def encoder(obj):
            if isinstance(obj, WebObjectBase):
                return obj.toMemoizedJSON()
            return obj

        data = json.loads(json.dumps(memoizedJson, default=encoder))
        self.sessionState.isConvertingToWireFormat = False
        return data

    def toMemoizedJSON(self):
        if not self.sessionState.useObjectIds or not self.sessionState.isConvertingToWireFormat:
            return {"objectDefinition_": self.objectDefinition_}
        if self.sessionState.usableObjectId(self.objectId_):
            return {"objectId_": self.objectId_}
        self.objectId_ = self.sessionState.allocateObjectId()
        return {"objectDefinition_": self.objectDefinition_, "objectId_": self.objectId_}

    def toJSON(self, objectId):
        return {"objectDefinition_": self.objectDefinition_, "objectId_": objectId}

    def get(self, field, callbacks):
        req = {
            'objectDefinition': self.toJSONWireFormat(),
            'messageType': 'Read',
            'field': field
            }
        def responseCallback(response, callbacks):
            if response['responseType'] == 'ReadResponse':
                self.triggerSuccessCallback(
                    callbacks,
                    self.sessionState.convertJsonToObject(response['value'])
                    )
            else:
                self.triggerFailureCallback(callbacks, response)
        self.sessionState.jsonInterface.send(req, lambda response: responseCallback(response, callbacks))
        self.sessionState.updateObjectIdThreshold()

    def subscribe(self, field, callbacks):
        req = {
            'objectDefinition': self.toJSONWireFormat(),
            'messageType': 'Subscribe',
            'field': field
            }
        def responseCallback(response, callbacks):
            if response['responseType'] == 'SubscribeResponse':
                self.triggerSuccessCallback(
                    callbacks,
                    self.sessionState.convertJsonToObject(response['value'])
                    )
            elif response['responseType'] == 'ValueChanged':
                self.triggerChangedCallback(
                    callbacks,
                    self.sessionState.convertJsonToObject(response['value'])
                    )
            else:
                self.triggerFailureCallback(callbacks, response)
        self.sessionState.jsonInterface.send(req, lambda response: responseCallback(response, callbacks))
        self.sessionState.updateObjectIdThreshold()

    def set(self, attributeName, value, callbacks):
        req = {
            'objectDefinition': self.toJSONWireFormat(),
            'messageType': 'Assign',
            'field': attributeName,
            'value': value
            }
        def responseCallback(response, callbacks):
            if response['responseType'] == 'OK':
                self.triggerSuccessCallback(callbacks)
            else:
                self.triggerFailureCallback(callbacks, response)
        self.sessionState.jsonInterface.send(req, lambda response: responseCallback(response, callbacks))
        self.sessionState.updateObjectIdThreshold()

    def invoke(self, name, args, callbacks):
        req = {
            'objectDefinition': self.toJSONWireFormat(),
            'messageType': 'Execute',
            'args': args,
            'field': name
            }
        def responseCallback(response, callbacks):
            if response['responseType'] == 'ExecutionResult':
                self.triggerSuccessCallback(
                    callbacks,
                    self.sessionState.convertJsonToObject(response['result'])
                    )
            else:
                self.triggerFailureCallback(callbacks, response)
        self.sessionState.jsonInterface.send(req, lambda response: responseCallback(response, callbacks))
        self.sessionState.updateObjectIdThreshold()

    @classmethod
    def triggerSuccessCallback(cls, callbacks, *args, **kwargs):
        return cls.triggerCallback(callbacks, 'onSuccess', *args, **kwargs)

    @classmethod
    def triggerFailureCallback(cls, callbacks, *args, **kwargs):
        return cls.triggerCallback(callbacks, 'onFailure', *args, **kwargs)

    @classmethod
    def triggerChangedCallback(cls, callbacks, *args, **kwargs):
        return cls.triggerCallback(callbacks, 'onChanged', *args, **kwargs)

    @staticmethod
    def triggerCallback(callbacks, name, *args, **kwargs):
        callback = getattr(callbacks, name, None) or callbacks.get(name)
        if callback:
            return callback(*args, **kwargs)



class SessionState(object):
    def __init__(self, maxObjectIds, useObjectIds, jsonInterface):
        self.useObjectIds = useObjectIds
        self.maxObjectIds = maxObjectIds
        self.minValidObjectId = 0
        self.curObjectId = 0
        self.jsonInterface = jsonInterface
        self.isConvertingToWireFormat = False
        self.objectsById = {}
        self.objectIdsMemoized = []
        self.timesCleared = 0

    def usableObjectId(self, objId):
        if objId is None:
            return False
        return objId >= self.minValidObjectId

    def allocateObjectId(self):
        self.curObjectId = self.curObjectId + 1
        return self.curObjectId - 1

    def updateObjectIdThreshold(self, forceFlush=False):
        if self.curObjectId > self.minValidObjectId + self.maxObjectIds or forceFlush:
            self.minValidObjectId = self.curObjectId
            req = {
                'messageType': 'ServerFlushObjectIdsBelow',
                'value': self.minValidObjectId,
                'objectDefinition': {}
                }
            self.jsonInterface.send(
                req,
                lambda x: x
                )

    def clearObjectIds(self):
        return self.updateObjectIdThreshold(True)

    def convertJsonToObject(self, val):
        if val is None:
            return

        if isinstance(val, list):
            return tuple(self.convertJsonToObject(x) for x in val)

        if not isinstance(val, dict):
            return val

        objectId = val.get('objectId_')
        if objectId is None:
            return {k: self.convertJsonToObject(v) for k, v in val.iteritems()}

        definition = val.get('objectDefinition_')
        if definition is None:
            objectToReturn = self.objectsById.get(objectId)
            if objectToReturn is None:
                raise Exception("Received an undefined object id: %s from the server" % objectId)
            return objectToReturn

        objectToReturn = (classes[definition['type']])(self, self.convertJsonToObject(definition['args']))
        self.objectsById[objectId] = objectToReturn
        self.objectIdsMemoized.append(objectId)
        return objectToReturn


    def clearObjectIdsBelow(self, minValidObjectId):
        self.timesCleared += 1
        self.objectIdsMemoized.sort()

        while len(self.objectIdsMemoized) > 0 and self.objectIdsMemoized[0] < minValidObjectId:
            objId = self.objectIdsMemoized.pop(0)
            del self.objectsById[objId]

class WebObjectFactory(object):
    def constructor(self, typeName):
        def construct(*args):
            return classes[typeName](self.sessionState, *args)
        return construct

    def __init__(self, jsonInterface, maxObjectIds=10000, useObjectIds=True):
        self.jsonInterface = jsonInterface
        self.sessionState = SessionState(maxObjectIds, useObjectIds, jsonInterface)

        self.jsonInterface.on('special_message', self.onSpecialMessage)
        self.__dict__.update({cls: self.constructor(cls) for cls in classes.iterkeys()})

    def onSpecialMessage(self, msg):
        if msg["responseType"] == 'ClientFlushObjectIdsBelow':
            self.sessionState.clearObjectIdsBelow(msg["value"])

    def flushObjectIds(self):
        return self.sessionState.clearObjectIds()

    def getJsonInterface(self):
        return self.jsonInterface
"""


def generatePythonWrapperForClass(lineWriter, className, classObj):
    lineWriter("")
    lineWriter("class %s(WebObjectBase):" % className)

    lineWriter = addSpaces(lineWriter)

    lineWriter("def __init__(self, sessionState, inArgs=None):")
    lineWriter('    super(%s, self).__init__(sessionState, inArgs)' % className)
    lineWriter("    self.objectDefinition_.update({")
    lineWriter('        "type": "%s",' % className)
    lineWriter('    })')
    lineWriter("")


    for memberName, memberDef in getClassMember(classObj).iteritems():
        if SubscribableObject.isPropertyToExpose(memberDef):
            lineWriter("def get_%s(self, callbacks):" % memberName)
            lineWriter("    self.get('%s', callbacks)" % memberName)
            lineWriter('')

            lineWriter("def subscribe_%s(self, callbacks):" % memberName)
            lineWriter("    self.subscribe('%s', callbacks)" % memberName)
            lineWriter('')

        if SubscribableObject.isFunctionToExpose(memberDef):
            lineWriter("def %s(self, args, callbacks):" % memberName)
            lineWriter("    self.invoke('%s', args, callbacks)" % memberName)
            lineWriter('')

def generatePythonWrapper(classMap):
    """Returns the text of a function 'createPythonInterface'"""
    outBuffer = StringIO.StringIO()
    lineWriter = lambda line: outBuffer.write(("        " + line).rstrip() + "\n")

    outBuffer.write(headerText + "\n")



    for className, classObj in classMap.iteritems():
        generatePythonWrapperForClass(
            lambda line: outBuffer.write(line.rstrip() + "\n"),
            className,
            classObj
            )

    outBuffer.write("\nclasses = {\n")
    for className, classObj in classMap.iteritems():
        outBuffer.write("    '%s': %s,\n" % (className, className))
    outBuffer.write("    }\n")

    # outBuffer.write("\nmodule.exports = SubscribableWebObjects if module?\n")

    return outBuffer.getvalue()

if __name__ == "__main__":
    import ufora.BackendGateway.SubscribableWebObjects.AllObjectClassesToExpose \
        as AllObjectClassesToExpose

    print generatePythonWrapper(AllObjectClassesToExpose.classMap)

