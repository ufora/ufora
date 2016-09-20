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
import pyfora.Exceptions as Exceptions
import pyfora.PyforaInspect as PyforaInspect
from pyfora.Unconvertible import Unconvertible
from pyfora.UnresolvedFreeVariableExceptions import UnresolvedFreeVariableException

import __builtin__
import ast
import logging
import traceback

class FreeVariableResolver(object):
    def __init__(self,
                 exclude_list=None,
                 terminal_value_filter=lambda _: True):
        if exclude_list is None:
            exclude_list = []
        self.exclude_list = exclude_list
        self.terminal_value_filter = terminal_value_filter

    def resolveFreeVariableMemberAccessChainsInAst(self,
                                                   pyObject,
                                                   pyAst,
                                                   freeMemberAccessChainsWithPositions,
                                                   convertedObjectCache):
        resolutions = {}

        for chainWithPosition in freeMemberAccessChainsWithPositions:
            if chainWithPosition and \
               chainWithPosition.var[0] in self.exclude_list:
                continue

            subchain, resolution, position = self._resolveChainInPyObject(
                chainWithPosition, pyObject, pyAst, convertedObjectCache
                )
            resolutions[subchain] = (resolution, position)

        return resolutions

    def resolveFreeVariableMemberAccessChains(self,
                                              freeVariableMemberAccessChainsWithPositions,
                                              boundVariables,
                                              convertedObjectCache):
        """ Return a dictionary mapping subchains to resolved ids."""
        resolutions = dict()

        for chainWithPosition in freeVariableMemberAccessChainsWithPositions:
            subchain, resolution, position = self.resolveChainByDict(
                chainWithPosition, boundVariables)

            if id(resolution) in convertedObjectCache:
                resolution = convertedObjectCache[id(resolution)][1]

            resolutions[subchain] = (resolution, position)

        return resolutions

    def resolveChainByDict(self, chainWithPosition, boundVariables):
        """
        `_resolveChainByDict`: look up a free variable member access chain, `chain`,
        in a dictionary of resolutions, `boundVariables`, or in `__builtin__` and
        return a tuple (subchain, resolution, location).
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in boundVariables:
            rootValue = boundVariables[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            raise UnresolvedFreeVariableException(chainWithPosition, None)

        return self.computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)


    def _resolveChainInPyObject(self,
                                chainWithPosition,
                                pyObject,
                                pyAst,
                                convertedObjectCache):
        """
        This name could be improved.

        Returns a `subchain, terminalPyValue, location` tuple: this represents
        the deepest value we can get to in the member chain `chain` on `pyObject`
        taking members only along modules (or "empty" modules)

        """
        subchainAndResolutionOrNone = self._subchainAndResolutionOrNone(pyObject,
                                                                        pyAst,
                                                                        chainWithPosition)
        if subchainAndResolutionOrNone is None:
            raise Exceptions.PythonToForaConversionError(
                "don't know how to resolve %s in %s (line:%s)"
                % (chainWithPosition.var, pyObject, chainWithPosition.pos.lineno)
                )

        subchain, terminalValue, location = subchainAndResolutionOrNone

        if id(terminalValue) in convertedObjectCache:
            terminalValue = convertedObjectCache[id(terminalValue)]

        return subchain, terminalValue, location

    def _subchainAndResolutionOrNone(self, pyObject, pyAst, chainWithPosition):
        if PyforaInspect.isfunction(pyObject):
            return self._lookupChainInFunction(pyObject, chainWithPosition)

        if PyforaInspect.isclass(pyObject):
            return self._lookupChainInClass(pyObject, pyAst, chainWithPosition)

        return None

    @staticmethod
    def _classMemberFunctions(pyObject):
        return PyforaInspect.getmembers(
            pyObject,
            lambda elt: PyforaInspect.ismethod(elt) or PyforaInspect.isfunction(elt)
            )

    def _lookupChainInClass(self, pyClass, pyAst, chainWithPosition):
        """
        return a pair `(subchain, subchainResolution)`
        where subchain resolves to subchainResolution in pyClass
        """
        memberFunctions = self._classMemberFunctions(pyClass)

        for _, func in memberFunctions:
            # lookup should be indpendent of which function we
            # actually choose. However, the unbound chain may not
            # appear in every member function
            try:
                return self._lookupChainInFunction(func, chainWithPosition)
            except UnresolvedFreeVariableException:
                pass

        baseClassResolutionOrNone = self._resolveChainByBaseClasses(
            pyClass, pyAst, chainWithPosition
            )
        if baseClassResolutionOrNone is not None:
            return baseClassResolutionOrNone

        raise UnresolvedFreeVariableException(chainWithPosition, None)

    def _resolveChainByBaseClasses(self, pyClass, pyAst, chainWithPosition):
        chain = chainWithPosition.var
        position = chainWithPosition.pos

        baseClassChains = [self._getBaseClassChain(base) for base in pyAst.bases]

        if chain in baseClassChains:
            resolution = pyClass.__bases__[baseClassChains.index(chain)]
            return chain, resolution, position

        # note: we could do better here. we could search the class
        # variables of the base class as well
        return None

    def _getBaseClassChain(self, baseAst):
        if isinstance(baseAst, ast.Name):
            return (baseAst.id,)
        if isinstance(baseAst, ast.Attribute):
            return self._getBaseClassChain(baseAst.value) + (baseAst.attr,)

    def _lookupChainInFunction(self, pyFunction, chainWithPosition):
        """
        return a tuple `(subchain, subchainResolution, location)`
        where subchain resolves to subchainResolution in pyFunction
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in pyFunction.func_code.co_freevars:
            index = pyFunction.func_code.co_freevars.index(freeVariable)
            try:
                rootValue = pyFunction.__closure__[index].cell_contents
            except Exception as e:
                logging.error("Encountered Exception: %s: %s", type(e).__name__, e)
                logging.error(
                    "Failed to get value for free variable %s\n%s",
                    freeVariable, traceback.format_exc())
                raise UnresolvedFreeVariableException(
                    chainWithPosition, pyFunction.func_name)

        elif freeVariable in pyFunction.func_globals:
            rootValue = pyFunction.func_globals[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            raise UnresolvedFreeVariableException(
                chainWithPosition, pyFunction.func_name)

        return self.computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)

    def computeSubchainAndTerminalValueAlongModules(self, rootValue, chainWithPosition):
        ix = 1
        chain = chainWithPosition.var
        position = chainWithPosition.pos

        subchain, terminalValue = chain[:ix], rootValue

        while PyforaInspect.ismodule(terminalValue) and self.terminal_value_filter(terminalValue):
            if ix >= len(chain):
                #we're terminating at a module
                terminalValue = Unconvertible(terminalValue)
                break

            if not hasattr(terminalValue, chain[ix]):
                raise Exceptions.PythonToForaConversionError(
                    "Module %s has no member %s" % (str(terminalValue), chain[ix])
                    )

            terminalValue = getattr(terminalValue, chain[ix])
            ix += 1
            subchain = chain[:ix]

        return subchain, terminalValue, position

