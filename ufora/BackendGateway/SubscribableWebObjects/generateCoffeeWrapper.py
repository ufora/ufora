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

import ufora.BackendGateway.SubscribableWebObjects.Decorators as Decorators

import cStringIO as StringIO
import json

def addSpaces(lineWriter):
    return lambda s: lineWriter("    " + s)

def getClassMember(cls):
    if cls is object:
        return {}

    prior = {}

    for c in reversed(cls.mro()):
        if c is not object:
            for x,val in c.__dict__.items():
                prior[x] = val

    return prior

preamble = """

curObjectId = 0
minValidObjectId = 0

allocateObjectId = ()->
    curObjectId = curObjectId + 1
    return curObjectId - 1

usableObjectId = (id) ->
    if not id?
        return false
    id >= minValidObjectId

updateObjectIdThreshold = (forceFlush = false) ->
    if curObjectId > minValidObjectId + maxObjectIds or forceFlush
        minValidObjectId = curObjectId
        req =
            messageType: 'ServerFlushObjectIdsBelow'
            value: minValidObjectId
            objectDefinition: {}
        jsonInterface.request req, (response) ->
            return

flushObjectIds = () -> updateObjectIdThreshold(true)

isConvertingToWireFormat = false

class IncomingObjectCache
    constructor: () ->
        @objectsById = {}
        @objectIdsMemoized = []
        @timesFlushed = 0

    convertJsonToObject: (val) ->
        if not val?
            return val
        objectId_ = val.objectId_
        if objectId_?
            def = val.objectDefinition_

            if def?
                objectToReturn = new (classes[def.type])(@convertJsonToObject(def.args))
                @objectsById[objectId_] = objectToReturn
                @objectIdsMemoized.push(objectId_)
                return objectToReturn
            else
                objectToReturn = @objectsById[objectId_]

                if not objectToReturn?
                    throw "Received an undefined object id: #{objectId_} from the server"
                return objectToReturn

        if val instanceof Array
            return (@convertJsonToObject(x) for x in val)
        if val instanceof Object
            res = {}
            res[y] = @convertJsonToObject(val[y]) for y of val
            return res
        return val

    flushObjectIdsBelow: (minValidObjectId) ->
        @timesFlushed += 1
        @objectIdsMemoized.sort()

        while @objectIdsMemoized.length > 0 and @objectIdsMemoized[0] < minValidObjectId
            id = @objectIdsMemoized.shift()
            delete @objectsById[id]

incomingObjectCache = new IncomingObjectCache()

jsonInterface.onUnknownMessage = (msg) ->
    if msg.responseType == 'ClientFlushObjectIdsBelow'
        incomingObjectCache.flushObjectIdsBelow(msg.value)

"""

def generateCoffeeWrapperForClass(lineWriter, className, classObj):
    lineWriter("")

    lineWriter("class %s" % className)

    lineWriter = addSpaces(lineWriter)

    lineWriter("constructor: (inArgs) -> ")
    lineWriter("    @objectDefinition_ = ")
    lineWriter('        type: "%s"' % className)
    lineWriter('        args: if inArgs? then inArgs else {}')
    lineWriter("")


    #create a wrapper function around our toJSON function that sets a module-level flag
    #this prevents users from accidentally allocating objectIDs and then not sending them over
    #the wire to the server
    lineWriter("toJSONWireFormat: () => ")
    lineWriter("    isConvertingToWireFormat = true")
    lineWriter("    data = JSON.parse(JSON.stringify(@))")
    lineWriter("    isConvertingToWireFormat = false")
    lineWriter("    data")

    #create a 'toJSON' function that allows the object to be serialized to JSON
    #This function gets run whenever we call 'JSON.stringify' or 'socket.emit'
    lineWriter("toJSON: () => ")
    lineWriter("    if not useObjectIds or not isConvertingToWireFormat")
    lineWriter("        return {objectDefinition_: @objectDefinition_}")
    lineWriter("    if usableObjectId(@objectId_)")
    lineWriter("        return {objectId_: @objectId_}")
    lineWriter("    @objectId_ = allocateObjectId()")
    lineWriter("    {objectDefinition_: @objectDefinition_, objectId_: @objectId_}")
    lineWriter("")

    for memberName, memberDef in getClassMember(classObj).iteritems():
        if Decorators.isPropertyToExpose(memberDef):
            if Decorators.propertyHasSetter(memberDef):
                lineWriter("set_%s: (value, callbacks) -> " % memberName)
                lineWriter("    req = ")
                lineWriter("        objectDefinition: @toJSONWireFormat()")
                lineWriter("        messageType: 'Assign'")
                lineWriter("        field: '%s'" % memberName)
                lineWriter("        value: value")
                lineWriter("    jsonInterface.request req, (response) -> ")
                lineWriter("        if response.responseType == 'OK'")
                lineWriter("            callbacks.onSuccess()")
                lineWriter("        else")
                lineWriter("            if callbacks.onFailure? then callbacks.onFailure (response)")
                lineWriter("    updateObjectIdThreshold()")

            lineWriter("get_%s: (callbacks) -> " % memberName)
            lineWriter("    req = ")
            lineWriter("        objectDefinition: @toJSONWireFormat()")
            lineWriter("        messageType: 'Read'")
            lineWriter("        field: '%s'" % memberName)
            lineWriter("    jsonInterface.request req, (response) -> ")
            lineWriter("        if response.responseType == 'ReadResponse'")
            lineWriter("            callbacks.onSuccess incomingObjectCache.convertJsonToObject(response.value)")
            lineWriter("        else")
            lineWriter("            if callbacks.onFailure? then callbacks.onFailure (response)")
            lineWriter("    updateObjectIdThreshold()")

            lineWriter("subscribe_%s: (callbacks) -> " % memberName)
            lineWriter("    req = ")
            lineWriter("        objectDefinition: @toJSONWireFormat()")
            lineWriter("        messageType: 'Subscribe'")
            lineWriter("        field: '%s'" % memberName)
            lineWriter("    jsonInterface.request req, (response) -> ")
            lineWriter("        if response.responseType == 'SubscribeResponse'")
            lineWriter("            callbacks.onSuccess incomingObjectCache.convertJsonToObject(response.value)")
            lineWriter("        else if response.responseType == 'ValueChanged'")
            lineWriter("            callbacks.onChanged incomingObjectCache.convertJsonToObject(response.value)")
            lineWriter("        else")
            lineWriter("            if callbacks.onFailure? then callbacks.onFailure (response)")
            lineWriter("    updateObjectIdThreshold()")

        if Decorators.isFunctionToExpose(memberDef):
            lineWriter("%s: (args, callbacks) -> " % memberName)
            lineWriter("    req = ")
            lineWriter("        objectDefinition: @toJSONWireFormat()")
            lineWriter("        messageType: 'Execute'")
            lineWriter("        args: args")
            lineWriter("        field: '%s'" % memberName)
            lineWriter("    jsonInterface.request req, (response) -> ")
            lineWriter("        if response.responseType == 'ExecutionResult'")
            lineWriter("            callbacks.onSuccess incomingObjectCache.convertJsonToObject(response.result)")
            lineWriter("        else")
            lineWriter("            if callbacks.onFailure? then callbacks.onFailure (response)")
            lineWriter("    updateObjectIdThreshold()")

def generateCoffeeWrapper(classMap):
    """Returns the text of a function 'createCoffeeInterface'"""
    outBuffer = StringIO.StringIO()

    outBuffer.write("SubscribableWebObjects = (jsonInterface, maxObjectIds = 10000, useObjectIds = true) ->\n")

    lineWriter = lambda line: outBuffer.write("    " + line + "\n")

    for line in preamble.split("\n"):
        lineWriter(line)

    for className, classObj in classMap.iteritems():
        generateCoffeeWrapperForClass(
            lineWriter,
            className,
            classObj
            )

    outBuffer.write("    classes = \n")
    for className, classObj in classMap.iteritems():
        outBuffer.write("        %s: %s\n" % (className, className))

    outBuffer.write("    result = \n")
    for className, classObj in classMap.iteritems():
        outBuffer.write("        %s: %s\n" % (className, className))
    outBuffer.write("        flushObjectIds:flushObjectIds\n")
    outBuffer.write("        getJsonInterface:()->jsonInterface\n")
    outBuffer.write("        incomingObjectCache:incomingObjectCache\n")
    outBuffer.write("    result\n")

    outBuffer.write("\nmodule.exports = SubscribableWebObjects if module?\n")

    return outBuffer.getvalue()

if __name__ == "__main__":
    import ufora.BackendGateway.SubscribableWebObjects.AllObjectClassesToExpose as AllObjectClassesToExpose

    print generateCoffeeWrapper(AllObjectClassesToExpose.classMap)

