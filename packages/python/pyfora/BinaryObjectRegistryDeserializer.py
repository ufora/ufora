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
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import json
import struct

class StringDeserializer:
    def __init__(self, s):
        self.data = s
        self.index = 0

    def finished(self):
        return self.index >= len(self.data)

    def readByte(self):
        res = struct.unpack("<b", self.data[self.index])[0]
        self.index += 1
        return res

    def readInt32(self):
        res = struct.unpack("<L", self.data[self.index:self.index+4])[0]
        self.index += 4
        return res

    def readInt64(self):
        res = struct.unpack("<q", self.data[self.index:self.index+8])[0]
        self.index += 8
        return res

    def readInt64s(self):
        count = self.readInt64()
        return [self.readInt64() for _ in xrange(count)]

    def readFloat64(self):
        res = struct.unpack("<d", self.data[self.index:self.index+8])[0]
        self.index += 8
        return res

    def readString(self):
        length = self.readInt32()
        res = self.data[self.index:self.index+length]
        self.index += length
        return res

def deserialize(data, objectWalker, convertJsonToObject):
    stream = StringDeserializer(data)

    while not stream.finished():
        objectId = stream.readInt64()
        code = stream.readByte()

        def readInt64s():
            return [stream.readInt64() for _ in xrange(stream.readInt64())]

        def readStringTuple():
            return tuple([stream.readString() for _ in xrange(stream.readInt32())])

        def readTupleScopeIds():
            res = {}
            ct = stream.readInt32()
            for _ in xrange(ct):
                path = tuple(stream.readString().split("."))
                objId = stream.readInt64()
                res[path] = objId
            return res

        def readDottedScopeIds():
            res = {}
            ct = stream.readInt32()
            for _ in xrange(ct):
                path = stream.readString()
                objId = stream.readInt64()
                res[path] = objId
            return res

        def readPrimitive(code):
            if code == BinaryObjectRegistry.CODE_NONE:
                return None
            elif code == BinaryObjectRegistry.CODE_INT:
                return stream.readInt64()
            elif code == BinaryObjectRegistry.CODE_LONG:
                return long(stream.readString())
            elif code == BinaryObjectRegistry.CODE_FLOAT:
                return stream.readFloat64()
            elif code == BinaryObjectRegistry.CODE_BOOL:
                return True if stream.readByte() else False
            elif code == BinaryObjectRegistry.CODE_STR:
                return stream.readString()
            elif code == BinaryObjectRegistry.CODE_LIST_OF_PRIMITIVES:
                return [readPrimitive(stream.readByte()) for _ in xrange(stream.readInt64())]
            else:
                assert False, "unknown code: " + str(code)

        if (code == BinaryObjectRegistry.CODE_NONE or 
                code == BinaryObjectRegistry.CODE_INT or
                code == BinaryObjectRegistry.CODE_LONG or
                code == BinaryObjectRegistry.CODE_FLOAT or
                code == BinaryObjectRegistry.CODE_BOOL or
                code == BinaryObjectRegistry.CODE_STR or
                code == BinaryObjectRegistry.CODE_LIST_OF_PRIMITIVES):
            objectWalker.definePrimitive(objectId, readPrimitive(code))
        elif code == BinaryObjectRegistry.CODE_TUPLE:
            objectWalker.defineTuple(objectId, readInt64s())
        elif code == BinaryObjectRegistry.CODE_PACKED_HOMOGENOUS_DATA:
            dtype = stream.readString()
            packedBytes = stream.readString()
            objectWalker.definePackedHomogenousData(objectId, TypeDescription.PackedHomogenousData(dtype, packedBytes))
        elif code == BinaryObjectRegistry.CODE_LIST:
            objectWalker.defineList(objectId, readInt64s())
        elif code == BinaryObjectRegistry.CODE_FILE:
            path = stream.readString()
            text = stream.readString()
            objectWalker.defineFile(objectId, text, path)
        elif code == BinaryObjectRegistry.CODE_DICT:
            objectWalker.defineDict(objectId, readInt64s(), readInt64s())
        elif code == BinaryObjectRegistry.CODE_REMOTE_PY_OBJECT:
            jsonRepresentation = json.loads(stream.readString())
            objectWalker.defineRemotePythonObject(objectId, convertJsonToObject(jsonRepresentation))
        elif code == BinaryObjectRegistry.CODE_BUILTIN_EXCEPTION_INSTANCE:
            objectWalker.defineBuiltinExceptionInstance(objectId, stream.readString(), stream.readInt64())
        elif code == BinaryObjectRegistry.CODE_NAMED_SINGLETON:
            objectWalker.defineNamedSingleton(objectId, stream.readString())
        elif code == BinaryObjectRegistry.CODE_FUNCTION:
            objectWalker.defineFunction(objectId, stream.readInt64(), stream.readInt32(), readDottedScopeIds())
        elif code == BinaryObjectRegistry.CODE_CLASS:
            objectWalker.defineClass(objectId, stream.readInt64(), stream.readInt32(), readDottedScopeIds(), readInt64s())
        elif code == BinaryObjectRegistry.CODE_UNCONVERTIBLE:
            if stream.readByte() != 0:
                objectWalker.defineUnconvertible(objectId, readStringTuple())
            else:
                objectWalker.defineUnconvertible(objectId, None)
        elif code == BinaryObjectRegistry.CODE_CLASS_INSTANCE:
            classId = stream.readInt64()
            classMembers = {}
            for _ in xrange(stream.readInt32()):
                memberName = stream.readString()
                classMembers[memberName] = stream.readInt64()
            objectWalker.defineClassInstance(objectId, classId, classMembers)
        elif code == BinaryObjectRegistry.CODE_INSTANCE_METHOD:
            objectWalker.defineInstanceMethod(objectId, stream.readInt64(), stream.readString())
        elif code == BinaryObjectRegistry.CODE_WITH_BLOCK:
            scopes = readDottedScopeIds()
            objectWalker.defineWithBlock(objectId, scopes, stream.readInt64(), stream.readInt32())
        else:
            assert False, "unknown code: " + str(code)

