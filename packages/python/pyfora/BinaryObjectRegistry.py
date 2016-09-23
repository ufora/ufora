#   Copyright 2016 Ufora Inc.
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

import pyfora.TypeDescription as TypeDescription
import base64
import struct
import json

class StringBuilder:
    """StringBuilder

    A simple class to build up a string out of little strings and perform some 
    simple binary serialization of objects.
    """
    def __init__(self):
        self.big_strings = []
        self.little_strings = []
        self.bytecount = 0

    def _add(self, s):
        self.bytecount += len(s)
        self.little_strings.append(s)
        if len(self.little_strings) > 10000:
            self.big_strings.append("".join(self.little_strings))
            self.little_strings = []

    def str(self):
        return "".join(self.big_strings + self.little_strings)

    def addByte(self, index):
        self._add(struct.pack("<b", index))

    def addInt32(self, index):
        self._add(struct.pack("<L", index))

    def addInt64(self, index):
        self._add(struct.pack("<q", index))

    def addInt64s(self, indices):
        self.addInt64(len(indices))
        for i in indices:
            self.addInt64(i)

    def addFloat64(self, index):
        self._add(struct.pack("<d", index))

    def addString(self, s):
        assert isinstance(s, str), type(s)
        self.addInt32(len(s))
        self._add(s)

    def addStringTuple(self, s):
        self.addInt32(len(s))
        for item in s:
            self.addString(item)


CODE_NONE=1
CODE_INT=2
CODE_LONG=3
CODE_FLOAT=4
CODE_BOOL=5
CODE_STR=6
CODE_LIST_OF_PRIMITIVES=7
CODE_TUPLE=8
CODE_PACKED_HOMOGENOUS_DATA=9
CODE_LIST=10
CODE_FILE=11
CODE_DICT=12
CODE_REMOTE_PY_OBJECT=13
CODE_BUILTIN_EXCEPTION_INSTANCE=14
CODE_NAMED_SINGLETON=15
CODE_FUNCTION=16
CODE_CLASS=17
CODE_UNCONVERTIBLE=18
CODE_CLASS_INSTANCE=19
CODE_INSTANCE_METHOD=20
CODE_WITH_BLOCK=21
CODE_PY_ABORT_EXCEPTION=22
CODE_STACKTRACE_AS_JSON=23

class BinaryObjectRegistry(object):
    """Plugin for the PyObjectWalker to push python objects into. Converts directly into a binary format."""
    def __init__(self):
        self._nextObjectID = 0
        self._builder = StringBuilder()
        self.unconvertibleIndices = set()

    def bytecount(self):
        return self._builder.bytecount

    def str(self):
        return self._builder.str()

    def clear(self):
        self._builder = StringBuilder()

    def getDefinition(self, objectId):
        return self.objectIdToObjectDefinition[objectId]

    def allocateObject(self):
        "get a unique id for an object to be inserted later in the registry"
        objectId = self._nextObjectID
        self._nextObjectID += 1
        return objectId

    def definePrimitive(self, objectId, primitive):
        self._builder.addInt64(objectId)
        self._writePrimitive(primitive)

    def _writePrimitive(self, primitive):
        if primitive is None:
            self._builder.addByte(CODE_NONE)
        #check bool before int, since bool is a subtype of int
        elif isinstance(primitive, bool):
            self._builder.addByte(CODE_BOOL)
            self._builder.addByte(1 if primitive else 0)
        elif isinstance(primitive, int):
            if -9223372036854775808 <= primitive <= 9223372036854775807:
                self._builder.addByte(CODE_INT)
                self._builder.addInt64(primitive)
            else:
                assert False, "integer is out of range. This should be a long."

        elif isinstance(primitive, long):
            self._builder.addByte(CODE_LONG)
            self._builder.addString(str(primitive))
        elif isinstance(primitive, float):
            self._builder.addByte(CODE_FLOAT)
            self._builder.addFloat64(primitive)
        elif isinstance(primitive, str):
            self._builder.addByte(CODE_STR)
            self._builder.addString(primitive)
        elif isinstance(primitive, list):
            self._builder.addByte(CODE_LIST_OF_PRIMITIVES)
            self._builder.addInt64(len(primitive))
            for p in primitive:
                self._writePrimitive(p)
        else:
            assert False, "Expected a primitive (none, bool, float, int, str)"

    def defineEndOfStream(self):
        self._builder.addInt64(-1)

    def defineTuple(self, objectId, memberIds):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_TUPLE)
        self._builder.addInt64s(memberIds)

    def definePackedHomogenousData(self, objectId, packedData):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_PACKED_HOMOGENOUS_DATA)
        def write(val):
            if val is None:
                self._builder.addByte(CODE_NONE)
            elif isinstance(val, int):
                self._builder.addByte(CODE_INT)
                self._builder.addInt64(val)
            elif isinstance(val, str):
                self._builder.addByte(CODE_STR)
                self._builder.addString(val)
            elif isinstance(val, tuple):
                self._builder.addByte(CODE_TUPLE)
                self._builder.addInt32(len(val))
                for v in val:
                    write(v)
            else:
                assert False, "unknown primitive in dtype: " + str(val)

        write(packedData.dtype)

        self._builder.addString(packedData.dataAsBytes)

    def defineList(self, objectId, memberIds):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_LIST)
        self._builder.addInt64s(memberIds)

    def defineFile(self, objectId, text, path):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_FILE)
        self._builder.addString(path)
        self._builder.addString(text)

    def defineDict(self, objectId, keyIds, valueIds):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_DICT)
        self._builder.addInt64s(keyIds)
        self._builder.addInt64s(valueIds)

    def defineRemotePythonObject(self, objectId, computedValueArg):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_REMOTE_PY_OBJECT)

        def encoder(obj):
            if hasattr(obj, "toMemoizedJSON"):
                return obj.toMemoizedJSON()
            return obj

        data = json.dumps(computedValueArg, default=encoder)

        self._builder.addString(data)

    def defineBuiltinExceptionInstance(self, objectId, typename, argsId):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_BUILTIN_EXCEPTION_INSTANCE)
        self._builder.addString(typename)
        self._builder.addInt64(argsId)

    def defineNamedSingleton(self, objectId, singletonName):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_NAMED_SINGLETON)
        self._builder.addString(singletonName)

    def defineFunction(self, objectId, sourceFileId, lineNumber, scopeIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        """
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_FUNCTION)
        self._builder.addInt64(sourceFileId)
        self._builder.addInt32(lineNumber)

        self._writeDottedScopeIds(scopeIds)

    def _writeTupleScopeIds(self, scopeIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        """
        self._builder.addInt32(len(scopeIds))
        for chain,childObjectId in scopeIds.iteritems():
            assert isinstance(chain, tuple)
            self._builder.addString(".".join(chain))
            self._builder.addInt64(childObjectId)

    def _writeDottedScopeIds(self, scopeIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        """
        self._builder.addInt32(len(scopeIds))
        for chain,childObjectId in scopeIds.iteritems():
            assert isinstance(chain, str)
            self._builder.addString(chain)
            self._builder.addInt64(childObjectId)

    def defineClass(self, objectId, sourceFileId, lineNumber, scopeIds, baseClassIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        baseClassIds: a list of ids representing (immediate) base classes
        """
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_CLASS)
        self._builder.addInt64(sourceFileId)
        self._builder.addInt32(lineNumber)
        self._writeDottedScopeIds(scopeIds)
        self._builder.addInt64s(baseClassIds)

    def isUnconvertible(self, objectId):
        return objectId in self.unconvertibleIndices

    def defineUnconvertible(self, objectId, modulePath):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_UNCONVERTIBLE)
        if modulePath is None:
            self._builder.addByte(0)
        else:
            self._builder.addByte(1)
            self._builder.addStringTuple(modulePath)
        self.unconvertibleIndices.add(objectId)

    def defineClassInstance(self, objectId, classId, classMemberNameToClassMemberId):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_CLASS_INSTANCE)
        self._builder.addInt64(classId)
        
        self._builder.addInt32(len(classMemberNameToClassMemberId))
        for k,v in classMemberNameToClassMemberId.iteritems():
            self._builder.addString(k)
            self._builder.addInt64(v)

    def defineInstanceMethod(self, objectId, instanceId, methodName):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_INSTANCE_METHOD)
        self._builder.addInt64(instanceId)
        self._builder.addString(methodName)
        
    def defineWithBlock(self,
                        objectId,
                        freeVariableMemberAccessChainsToId,
                        sourceFileId,
                        lineNumber):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_WITH_BLOCK)
        self._writeDottedScopeIds(freeVariableMemberAccessChainsToId)
        self._builder.addInt64(sourceFileId)
        self._builder.addInt32(lineNumber)
    
    def definePyAbortException(self, objectId, typename, argsId):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_PY_ABORT_EXCEPTION)
        self._builder.addString(typename)
        self._builder.addInt64(argsId)

    def defineStacktrace(self, objectId, stacktraceAsJson):
        self._builder.addInt64(objectId)
        self._builder.addByte(CODE_STACKTRACE_AS_JSON)
        self._builder.addString(json.dumps(stacktraceAsJson))


