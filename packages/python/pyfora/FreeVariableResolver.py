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

import __builtin__
import ast
from collections import namedtuple
import logging
import traceback


class ResolutionResult(object):
    Resolution = namedtuple("Resolution", "subchain resolution position")
    Unbound = namedtuple("Unbound", "name")

    is_resolution_flag, is_unbound_flag = 0, 1

    def __init__(self, flag, value):
        self.flag = flag
        self.value = value

    @staticmethod
    def resolution(subchain, resolution, position):
        value = ResolutionResult.Resolution(subchain=subchain,
                                            resolution=resolution,
                                            position=position)
        return ResolutionResult(flag=ResolutionResult.is_resolution_flag, value=value)

    @staticmethod
    def unbound(name):
        value = ResolutionResult.Unbound(name=name)
        return ResolutionResult(flag=ResolutionResult.is_unbound_flag, value=value)

    def isResultion(self):
        return self.flag == ResolutionResult.is_resolution_flag

    def isUnbound(self):
        return self.flag == ResolutionResult.is_unbound_flag


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
        unresolvable_symbols = set()

        for chainWithPosition in freeMemberAccessChainsWithPositions:
            if chainWithPosition and \
               chainWithPosition.var[0] in self.exclude_list:
                continue

            resolutionResult = self._resolveChainInPyObject(
                chainWithPosition, pyObject, pyAst, convertedObjectCache
                )

            if resolutionResult.isResultion():
                subchain, resolution, position = resolutionResult.value
                resolutions[subchain] = (resolution, position)
            else:
                unresolvable_symbols.add(resolutionResult.value.name)

        return resolutions, unresolvable_symbols

    def resolveFreeVariableMemberAccessChains(self,
                                              freeVariableMemberAccessChainsWithPositions,
                                              boundVariables,
                                              convertedObjectCache):
        """ Return a pair: a dictionary mapping subchains to resolved ids,
                           and a set giving the names of the unresolvable symbols.
        """
        resolutions = dict()
        unresolvable_symbols = set()

        for chainWithPosition in freeVariableMemberAccessChainsWithPositions:
            resolutionResult = self.resolveChainByDict(chainWithPosition, boundVariables)

            if resolutionResult.isResultion():
                subchain, resolution, position = resolutionResult.value

                if id(resolution) in convertedObjectCache:
                    resolution = convertedObjectCache[id(resolution)][1]

                resolutions[subchain] = (resolution, position)
            else:
                unresolvable_symbols.add(resolutionResult.value.name)

        return resolutions, unresolvable_symbols

    def resolveChainByDict(self, chainWithPosition, boundVariables):
        """
        `_resolveChainByDict`: look up a free variable member access chain, `chain`,
        in a dictionary of resolutions, `boundVariables`, or in `__builtin__` and
        return a tuple (subchain, resolution, location).

        returns a ResolutionResult
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in boundVariables:
            rootValue = boundVariables[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            return ResolutionResult.unbound(chainWithPosition)

        return self.computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)


    def _resolveChainInPyObject(self,
                                chainWithPosition,
                                pyObject,
                                pyAst,
                                convertedObjectCache):
        """
        Returns a ResolutionResult.Resolution 
        `subchain, terminalPyValue, location` tuple: this represents
        the deepest value we can get to in the member chain `chain` on `pyObject`
        taking members only along modules (or "empty" modules)

        """
        resolutionResult = self._lookupChainInFunctionOrClass(pyObject,
                                                              pyAst,
                                                              chainWithPosition)

        if resolutionResult.isResultion():
            subchain, terminalValue, position = resolutionResult.value

            if id(terminalValue) in convertedObjectCache:
                terminalValue = convertedObjectCache[id(terminalValue)]
                resolutionResult = ResolutionResult.resolution(subchain=subchain,
                                                               resolution=terminalValue,
                                                               position=position)

        return resolutionResult

    def _lookupChainInFunctionOrClass(self, pyObject, pyAst, chainWithPosition):
        if PyforaInspect.isfunction(pyObject):
            return self._lookupChainInFunction(pyObject, chainWithPosition)

        if PyforaInspect.isclass(pyObject):
            return self._lookupChainInClass(pyObject, pyAst, chainWithPosition)

        assert False, "should only have functions or classes here"

    @staticmethod
    def _classMemberFunctions(pyObject):
        return PyforaInspect.getmembers(
            pyObject,
            lambda elt: PyforaInspect.ismethod(elt) or PyforaInspect.isfunction(elt)
            )

    def _lookupChainInClass(self, pyClass, pyAst, chainWithPosition):
        """
        returns a ResolutionResult
        """
        memberFunctions = self._classMemberFunctions(pyClass)

        for _, func in memberFunctions:
            # lookup should be indpendent of which function we
            # actually choose. However, the unbound chain may not
            # appear in every member function
            candidate = self._lookupChainInFunction(func, chainWithPosition)

            if candidate.isResultion():
                return candidate

        return self._resolveChainByBaseClasses(pyClass, pyAst, chainWithPosition)

    def _resolveChainByBaseClasses(self, pyClass, pyAst, chainWithPosition):
        chain = chainWithPosition.var
        position = chainWithPosition.pos

        baseClassChains = [self._getBaseClassChain(base) for base in pyAst.bases]

        if chain in baseClassChains:
            resolution = pyClass.__bases__[baseClassChains.index(chain)]
            return ResolutionResult.resolution(
                subchain=chain,
                resolution=resolution,
                position=position)

        # note: we could do better here. we could search the class
        # variables of the base class as well
        return ResolutionResult.unbound(chainWithPosition)

    def _getBaseClassChain(self, baseAst):
        if isinstance(baseAst, ast.Name):
            return (baseAst.id,)
        if isinstance(baseAst, ast.Attribute):
            return self._getBaseClassChain(baseAst.value) + (baseAst.attr,)

    def _lookupChainInFunction(self, pyFunction, chainWithPosition):
        """
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in pyFunction.func_code.co_freevars:
            index = pyFunction.func_code.co_freevars.index(freeVariable)
            try:
                rootValue = pyFunction.__closure__[index].cell_contents
            except Exception as e:
                logging.error("Encountered Exception: %s: %s", type(e).__name__, e)
                logging.error(
                    "Failed to get value for free variable %s in function %s\n%s",
                    freeVariable,
                    pyFunction.func_name,
                    traceback.format_exc())
                return ResolutionResult.unbound(chainWithPosition)

        elif freeVariable in pyFunction.func_globals:
            rootValue = pyFunction.func_globals[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            return ResolutionResult.unbound(chainWithPosition)

        return self.computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)

    def computeSubchainAndTerminalValueAlongModules(self, rootValue, chainWithPosition):
        """
        Return a ResultionResult or raise a PythonToForaConversionError
        """
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

        return ResolutionResult.resolution(subchain=subchain,
                                           resolution=terminalValue,
                                           position=position)

