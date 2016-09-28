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
import os
import struct

class Deserializer:
    def readByte(self):
        res = struct.unpack("<b", self.grabBytes(1))[0]
        return res

    def readInt32(self):
        res = struct.unpack("<L", self.grabBytes(4))[0]
        return res

    def readInt64(self):
        res = struct.unpack("<q", self.grabBytes(8))[0]
        return res

    def readInt64s(self):
        count = self.readInt64()
        return [self.readInt64() for _ in xrange(count)]

    def readFloat64(self):
        res = struct.unpack("<d", self.grabBytes(8))[0]
        return res

    def readString(self):
        length = self.readInt32()
        res = self.grabBytes(length)
        return res


class StringDeserializer(Deserializer):
    def __init__(self, s):
        self.data = s
        self.index = 0

    def grabBytes(self, bytecount):
        res = self.data[self.index:self.index+bytecount]
        self.index += bytecount
        return res

class FileDescriptorDeserializer(Deserializer):
    def __init__(self, fd):
        self.fd = fd

    def grabBytes(self, bytecount):
        res = os.read(self.fd, bytecount)
        assert len(res) == bytecount, "Stream terminated unexpectedly"
        return res

def deserializeFromFileDescriptor(fd, objectVisitor, convertJsonToObject):
    stream = FileDescriptorDeserializer(fd)

    return deserializeFromStream(stream, objectVisitor, convertJsonToObject)


def deserializeFromString(data, objectVisitor, convertJsonToObject):
    stream = StringDeserializer(data)

    return deserializeFromStream(stream, objectVisitor, convertJsonToObject)

def deserializeFromStream(stream, objectVisitor, convertJsonToObject):
    while True:
        objectId = stream.readInt64()

        #this is the termination condition
        if objectId == -1:
            return

        code = stream.readByte()

        def readSimplePrimitive():
            code = stream.readByte()
            if code == BinaryObjectRegistry.CODE_NONE:
                return None
            if code == BinaryObjectRegistry.CODE_INT:
                return stream.readInt64()
            if code == BinaryObjectRegistry.CODE_STR:
                return stream.readString()
            if code == BinaryObjectRegistry.CODE_TUPLE:
                ct = stream.readInt32()
                return tuple([readSimplePrimitive() for _ in xrange(ct)])
            if code == BinaryObjectRegistry.CODE_LIST:
                ct = stream.readInt32()
                return [readSimplePrimitive() for _ in xrange(ct)]
            if code == BinaryObjectRegistry.CODE_DICT:
                ct = stream.readInt32()
                return dict([(readSimplePrimitive(),readSimplePrimitive()) for _ in xrange(ct)])
            else:
                assert False, "unknown code: " + str(code)
            

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
            objectVisitor.definePrimitive(objectId, readPrimitive(code))
        elif code == BinaryObjectRegistry.CODE_TUPLE:
            objectVisitor.defineTuple(objectId, readInt64s())
        elif code == BinaryObjectRegistry.CODE_PACKED_HOMOGENOUS_DATA:
            dtype = readSimplePrimitive()
            packedBytes = stream.readString()
            objectVisitor.definePackedHomogenousData(objectId, TypeDescription.PackedHomogenousData(dtype, packedBytes))
        elif code == BinaryObjectRegistry.CODE_LIST:
            objectVisitor.defineList(objectId, readInt64s())
        elif code == BinaryObjectRegistry.CODE_FILE:
            path = stream.readString()
            text = stream.readString()
            objectVisitor.defineFile(objectId, text, path)
        elif code == BinaryObjectRegistry.CODE_DICT:
            objectVisitor.defineDict(objectId, readInt64s(), readInt64s())
        elif code == BinaryObjectRegistry.CODE_REMOTE_PY_OBJECT:
            jsonRepresentation = json.loads(stream.readString())
            objectVisitor.defineRemotePythonObject(objectId, convertJsonToObject(jsonRepresentation))
        elif code == BinaryObjectRegistry.CODE_BUILTIN_EXCEPTION_INSTANCE:
            objectVisitor.defineBuiltinExceptionInstance(objectId, stream.readString(), stream.readInt64())
        elif code == BinaryObjectRegistry.CODE_NAMED_SINGLETON:
            objectVisitor.defineNamedSingleton(objectId, stream.readString())
        elif code == BinaryObjectRegistry.CODE_FUNCTION:
            objectVisitor.defineFunction(objectId, stream.readInt64(), stream.readInt32(), readDottedScopeIds())
        elif code == BinaryObjectRegistry.CODE_CLASS:
            objectVisitor.defineClass(objectId, stream.readInt64(), stream.readInt32(), readDottedScopeIds(), readInt64s())
        elif code == BinaryObjectRegistry.CODE_UNCONVERTIBLE:
            if stream.readByte() != 0:
                objectVisitor.defineUnconvertible(objectId, readStringTuple())
            else:
                objectVisitor.defineUnconvertible(objectId, None)
        elif code == BinaryObjectRegistry.CODE_CLASS_INSTANCE:
            classId = stream.readInt64()
            classMembers = {}
            for _ in xrange(stream.readInt32()):
                memberName = stream.readString()
                classMembers[memberName] = stream.readInt64()
            objectVisitor.defineClassInstance(objectId, classId, classMembers)
        elif code == BinaryObjectRegistry.CODE_INSTANCE_METHOD:
            objectVisitor.defineInstanceMethod(objectId, stream.readInt64(), stream.readString())
        elif code == BinaryObjectRegistry.CODE_WITH_BLOCK:
            scopes = readDottedScopeIds()
            objectVisitor.defineWithBlock(objectId, scopes, stream.readInt64(), stream.readInt32())
        elif code == BinaryObjectRegistry.CODE_PY_ABORT_EXCEPTION:
            typename = stream.readString()
            argsId = stream.readInt64()
            objectVisitor.definePyAbortException(objectId, typename, argsId)
        elif code == BinaryObjectRegistry.CODE_STACKTRACE_AS_JSON:
            stackAsJson = stream.readString()
            objectVisitor.defineStacktrace(objectId, json.loads(stackAsJson))
        else:
            assert False, "unknown code: " + str(code)

