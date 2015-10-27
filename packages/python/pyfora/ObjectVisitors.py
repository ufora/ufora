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

import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectVisitorBase as ObjectVisitorBase
import pyfora.PyObjectNodes as PyObjectNodes
import logging

class ObjectIdVisitor(ObjectVisitorBase.ObjectVisitorBase):
    """
    Used as a visitor of PyObjectWalker to populate objectRegistry and pyObjectIdToObjectId.

    pyObjectIdToObjectId: { pyObjectID -> objectID }
    pyObjectID: id(pyObject)
    objectID: is *not* id(object) but the index of object in the objectRegistry.
    """
    def __init__(self, objectRegistry):
        super(ObjectIdVisitor, self).__init__()

        self.objectRegistry = objectRegistry
        self.pyObjectIdToObjectId = {}

    def _visit_node(self, node):
        self._visit_pyObject(node.pyObject)

    def _visit_pyObject(self, pyObject):
        objectId = self.objectRegistry.allocateObject()

        self.pyObjectIdToObjectId[id(pyObject)] = (pyObject, objectId)

    def visit_File(self, node):
        self._visit_node(node)

    def visit_Primitive(self, node):
        self._visit_node(node)

    def visit_ClassInstanceDescription(self, node):
        self._visit_node(node)

    def visit_FunctionDefinition(self, node):
        self._visit_node(node)

    def visit_ClassDefinition(self, node):
        self._visit_node(node)

    def visit_List(self, node):
        self._visit_node(node)

    def visit_Tuple(self, node):
        self._visit_node(node)

    def visit_Dict(self, node):
        self._visit_node(node)

    def visit_RemotePythonObject(self, node):
        self._visit_node(node)

    def visit_BuiltinExceptionInstance(self, node):
        self._visit_node(node)

    def visit_NamedSingleton(self, node):
        self._visit_node(node)

    def visit_WithBlock(self, node):
        self._visit_node(node)

class ObjectVisitor(ObjectVisitorBase.ObjectVisitorBase):
    """
    This class badly needs a better name. What he does is visit nodes that a PyObjectWalker
    traverses, and calls appropriate methods on a pyfora.objectRegistry object as it goes.

    This "defines" objects on the server, by passing descriptions of the objects.
    """
    def __init__(self, objectRegistry, pyObjectIdToObjectId):
        super(ObjectVisitor, self).__init__()

        self.objectRegistry = objectRegistry
        self.pyObjectIdToObjectId = pyObjectIdToObjectId

    def _objectIdFor(self, node):
        if isinstance(node, PyObjectNodes.PyObjectNode):
            return self.pyObjectIdToObjectId[id(node.pyObject)][1]

        try:
            return self.pyObjectIdToObjectId[id(node)][1]
        except:
            logging.error("Failed on %s", node)
            raise

    def visit_Primitive(self, primitive):
        objectId = self._objectIdFor(primitive.pyObject)

        # could insert some instructions for using a wrapper class here ...
        self.objectRegistry.definePrimitive(objectId, primitive.pyObject)

    def visit_NamedSingleton(self, namedSingleton):
        objectId = self._objectIdFor(namedSingleton.pyObject)

        self.objectRegistry.defineNamedSingleton(objectId, namedSingleton.singletonName)

    def visit_BuiltinExceptionInstance(self, instance):
        objectId = self._objectIdFor(instance.pyObject)

        self.objectRegistry.defineBuiltinExceptionInstance(
            objectId, 
            instance.builtinExceptionTypeName, 
            self._objectIdFor(instance.args)
            )

    def visit_RemotePythonObject(self, pyObject):
        objectId = self._objectIdFor(pyObject.pyObject)

        self.objectRegistry.defineRemotePythonObject(objectId, pyObject.computedValueArg)

    def visit_WithBlock(self, withBlock):
        objectId = self._objectIdFor(withBlock.pyObject)

        freeVariableMemberAccessChainsToId = self._computeScopeIds(
            withBlock.freeVariableMemberAccessChainResolutions
            )

        self.objectRegistry.defineWithBlock(
            objectId=objectId,
            freeVariableMemberAccessChainsToId=\
                freeVariableMemberAccessChainsToId,
            sourceFileId=self._objectIdFor(withBlock.sourceFile),
            lineNumber=withBlock.lineNumber
            )

    def visit_Tuple(self, tuple_):
        pyTuple = tuple_.pyObject
        objectId = self._objectIdFor(pyTuple)

        self.objectRegistry.defineTuple(
            objectId=objectId,
            memberIds=[self._objectIdFor(member) for member in pyTuple]
            )

    def visit_List(self, list_):
        pyList = list_.pyObject
        objectId = self._objectIdFor(pyList)

        self.objectRegistry.defineList(
            objectId=objectId,
            memberIds=[self._objectIdFor(member) for member in pyList]
            )

    def visit_Dict(self, dict_):
        pyDict = dict_.pyObject
        objectId = self._objectIdFor(pyDict)

        self.objectRegistry.defineDict(
            objectId=objectId,
            keyIds=[self._objectIdFor(key) for key in pyDict.keys()],
            valueIds=[self._objectIdFor(value) for value in pyDict.values()]
            )

    def visit_File(self, fileDescription):
        objectId = self._objectIdFor(fileDescription.pyObject)

        self.objectRegistry.defineFile(
            objectId=objectId,
            path=fileDescription.path,
            text=fileDescription.pyObject
            )

    def visit_FunctionDefinition(self, functionDefinition):
        objectId = self._objectIdFor(functionDefinition.pyObject)

        self.objectRegistry.defineFunction(
            objectId=objectId,
            sourceFileId=self._objectIdFor(functionDefinition.sourceFile),
            lineNumber=functionDefinition.lineNumber,
            scopeIds=self._computeScopeIds(
                functionDefinition.freeVariableMemberAccessChainResolutions
                )
            )

    def visit_ClassDefinition(self, classDefinition):
        objectId = self._objectIdFor(classDefinition.pyObject)

        self.objectRegistry.defineClass(
            objectId=objectId,
            sourceFileId=self._objectIdFor(classDefinition.sourceFile),
            lineNumber=classDefinition.lineNumber,
            scopeIds=self._computeScopeIds(
                classDefinition.freeVariableMemberAccessChainResolutions
                )
            )

    def visit_ClassInstanceDescription(self, classInstanceDescription):
        objectId = self._objectIdFor(classInstanceDescription.pyObject)

        self.objectRegistry.defineClassInstance(
            objectId=objectId,
            classId=self._objectIdFor(classInstanceDescription.klass),
            classMemberNameToClassMemberId={
                name: self._objectIdFor(value)
                for name, value in classInstanceDescription.classMemberNameToMemberValue.iteritems()
                }
            )

    def _computeScopeIds(self, freeVariableMemberAccessChainResolutions):
        return {
            key: self._objectIdFor(val) for \
            key, val in freeVariableMemberAccessChainResolutions.iteritems()
            }

def walkPythonObject(pyObject,
                     objectRegistry,
                     purePythonClassMapping=None):
    """
    walk the python object `pyObject` in two passes,
    each time communicating with `objectRegistry`

    The first pass assigns ids to the nodes in `pyObject`.
    The second pass calls the appropriate `define*` methods on
    `objectRegistry` for the values it passes.

    In the end, return the object id of the converted value.

    purePythonClassMapping -- an instance of PureImplementationMappings
    """

    idVisitor = ObjectIdVisitor(
        objectRegistry=objectRegistry
        )

    pyObjectWalker = PyObjectWalker.PyObjectWalker(
        idVisitor,
        purePythonClassMapping=purePythonClassMapping
        )

    pyObjectWalker.walkPyObject(pyObject)

    objectVisitor = ObjectVisitor(
        objectRegistry,
        pyObjectIdToObjectId=idVisitor.pyObjectIdToObjectId
        )

    pyObjectWalker.resetWalkedNodes()
    pyObjectWalker.setVisitor(objectVisitor)

    pyObjectWalker.walkPyObject(pyObject)

    pyObject = pyObjectWalker.unwrapConvertedObject(pyObject)
    
    try:
        return objectVisitor.pyObjectIdToObjectId[id(pyObject)][1]
    except:
        logging.error("Failed with %s of type (%s)", pyObject, type(pyObject))
        raise

