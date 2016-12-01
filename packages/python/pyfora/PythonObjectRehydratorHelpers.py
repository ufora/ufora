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

import ast
import copy
import logging
import os
import sys
import traceback

import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions
import pyfora.pyAst.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora


def noConversion(*args):
    assert False, "Not implemented yet"


def sanitizeModulePath(pathToModule):
    res = os.path.abspath(pathToModule)
    if res.endswith(".pyc"):
        res = res[:-1]
    return res


@PyAstUtil.CachedByArgs
def updatePyAstMemberChains(pyAst, variablesInScope, isClassContext):
    #in the variables we've been handed, every member access chain 'x.y.z' has been
    #replaced with an actual variable lookup of the form 'x.y.z'. We need to perform
    #this same replacement in the actual python source code we're running, since
    #we may not actually have enough information to recover 'x'

    replacements = {}
    for possible_replacement in variablesInScope:
        if '.' in possible_replacement:
            replacements[tuple(possible_replacement.split('.'))] = possible_replacement

    #we need to deepcopy the AST since the collapser modifies the AST, and this is just a 
    #slice of a cached tree.
    pyAst = ast.fix_missing_locations(copy.deepcopy(pyAst))

    pyAst = PyAstFreeVariableAnalyses.collapseFreeVariableMemberAccessChains(
        pyAst,
        replacements,
        isClassContext=isClassContext)

    return ast.fix_missing_locations(pyAst)


class PythonObjectRehydratorHelpers(object):
    """
    PythonObjectRehydratorHelpers - py methods implementing part of 
    the CPP PythonObjectRehydrator
    """
    def __init__(self, purePythonClassMapping, allowUserCodeModuleLevelLookups=True):
        self.allowUserCodeModuleLevelLookups = allowUserCodeModuleLevelLookups
        self.moduleClassesAndFunctionsByPath = {}
        self.pathsToModules = {}
        self.purePythonClassMapping = purePythonClassMapping
        self.loadPathsToModules()

    def loadPathsToModules(self):
        for module in list(sys.modules.itervalues()):
            if module is not None:
                if hasattr(module, '__file__'):
                    self.pathsToModules[sanitizeModulePath(module.__file__)] = module


    def moduleLevelObject(self, path, lineNumber):
        if path not in self.moduleClassesAndFunctionsByPath:
            self.populateModuleMembers(path)

        if lineNumber in self.moduleClassesAndFunctionsByPath[path]:
            return self.moduleClassesAndFunctionsByPath[path][lineNumber]
 
        return None

    def canPopulateForPath(self, path):
        if self.allowUserCodeModuleLevelLookups:
            return True

        if path.startswith(sys.prefix) or path.startswith(pyfora.__path__[0]):
            #check if this is user code
            return True

        return False

    def populateModuleMembers(self, path):
        if path in self.moduleClassesAndFunctionsByPath:
            return

        res = self.moduleClassesAndFunctionsByPath[path] = {}
        module = self.moduleForFile(path)

        if module is not None and self.canPopulateForPath(path):
            for leafItemName in module.__dict__:
                leafItemValue = module.__dict__[leafItemName]

                if PyforaInspect.isclass(leafItemValue) or PyforaInspect.isfunction(leafItemValue):
                    try:
                        sourcePath = PyforaInspect.getsourcefile(leafItemValue)

                        if sourcePath is not None:
                            if os.path.samefile(path, sourcePath):
                                _, lineNumber = PyforaInspect.findsource(leafItemValue)

                                lineNumberToUse = lineNumber + 1

                                if lineNumberToUse in res and res[lineNumberToUse] is not leafItemValue:
                                    raise Exceptions.ForaToPythonConversionError(
                                        ("PythonObjectRehydratorHelpers got a line number collision at lineNumber %s"
                                         ", between %s and %s"),
                                        lineNumberToUse,
                                        leafItemValue,
                                        res[lineNumber + 1]
                                        )

                                res[lineNumberToUse] = leafItemValue
                            else:
                                self.populateModuleMembers(sourcePath)
                        
                    except Exceptions.ForaToPythonConversionError:
                        raise
                    except PyforaInspect.PyforaInspectError:
                        pass
                    except IOError:
                        #this gets raised when PyforaInspect can't find a file it needs
                        pass
                    except Exception as e:
                        logging.critical("PyforaInspect threw an exception: %s. tb = %s",
                                         e,
                                         traceback.format_exc())

    def moduleForFile(self, path):
        path = sanitizeModulePath(path)
        
        if path not in self.pathsToModules:
            self.loadPathsToModules()

        return self.pathsToModules.get(path)

    def importModuleMagicVariables(self, targetDict, path):
        """Find the module at 'path' and set 'targetDict' to have the same magic
           vars (e.g. module path etc.)"""
        actualModule = self.moduleForFile(path)
        if actualModule is not None:
            for magicVar in ['__file__', '__path__', '__name__', '__package__']:
                if hasattr(actualModule, magicVar):
                    targetDict[magicVar] = getattr(actualModule, magicVar)


    def _invertPureClassInstanceIfNecessary(self, instance):
        if self.purePythonClassMapping.canInvert(instance):
            return self.purePythonClassMapping.pureInstanceToMappable(instance)
        return instance


    def classObjectFromFile(self, filedescription, lineNumber, members):
        return self.classObjectFromFilenameAndLine(
            filedescription.path,
            lineNumber,
            members,
            filedescription.text
            )


    def classObjectFromFilenameAndLine(self, filename, lineNumber, members, fileText):
        """Construct a class object given its textual definition."""
        assert fileText is not None

        objectOrNone = self.moduleLevelObject(filename, lineNumber)

        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.pyAstFromText(fileText)
        classAst = PyAstUtil.classDefAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(members)

        self.importModuleMagicVariables(globalScope, filename)

        try:
            moduleAst = updatePyAstMemberChains(ast.Module([classAst]),
                                                tuple(globalScope.keys()),
                                                isClassContext=False)

            code = compile(moduleAst, filename, 'exec')

            exec code in globalScope, outputLocals
        except:
            logging.error("Failed to instantiate class at %s:%s\n%s",
                          filename,
                          lineNumber,
                          traceback.format_exc())
            raise Exceptions.PyforaError(
                "Failed to instantiate class at %s:%s" % (filename, lineNumber)
                )

        assert len(outputLocals) == 1

        return list(outputLocals.values())[0]


    def instantiateClass(self, classObject, memberDictionary):
        """Instantiate a class given its defined methods."""
        if '__init__' in dir(classObject):
            origInit = classObject.__init__
            def alteredInit(self, **kwds):
                self.__dict__.update(kwds)
            classObject.__init__ = alteredInit

            res = classObject(**memberDictionary)

            classObject.__init__ = origInit
        else:
            assert len(memberDictionary) == 0
            return classObject()

        return res

        
    def instantiateFunctionFromFile(self, filedescription, lineNumber, members):
        return self.instantiateFunction(
            filedescription.path,
            lineNumber,
            members,
            filedescription.text
            )


    def instantiateFunction(self, filename, lineNumber, memberDictionary, file_text):
        """Instantiate a function instance."""
        objectOrNone = self.moduleLevelObject(filename, lineNumber)
        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.pyAstFromText(file_text)
        functionAst = PyAstUtil.functionDefOrLambdaOrWithBlockAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(memberDictionary)
        self.importModuleMagicVariables(globalScope, filename)

        if isinstance(functionAst, ast.Lambda):
            expr = ast.FunctionDef()
            expr.name = '__pyfora_lambda_builder__'
            expr.args = ast.arguments()
            expr.args.args = []
            expr.args.defaults = []
            expr.args.vararg = None
            expr.args.kwarg = None

            expr.decorator_list = []
            expr.lineno = functionAst.lineno-1
            expr.col_offset = functionAst.col_offset

            return_statement = ast.Return(functionAst)
            expr.body = [return_statement]

            expr = updatePyAstMemberChains(ast.Module([expr], lineno=1,col_offset=0), tuple(globalScope.keys()), isClassContext=True)

            code = compile(expr, filename, 'exec')

            exec code in globalScope, outputLocals

            return list(outputLocals.values())[0]()

        elif isinstance(functionAst, ast.With):
            expr = ast.FunctionDef()
            expr.name = '__pyfora_with_block_as_function__'
            expr.args = ast.arguments()
            expr.args.args = []
            expr.args.defaults = []
            expr.args.vararg = None
            expr.args.kwarg = None

            expr.decorator_list = []
            
            #make sure we copy the list - if we use the existing one, we will mess up the
            #cached copy!
            expr.body = list(functionAst.body)
            expr.lineno = functionAst.lineno-1
            expr.col_offset = functionAst.col_offset

            bound_variables = PyAstFreeVariableAnalyses.collectBoundValuesInScope(expr)

            return_dict_list_src = "[" + ",".join("'%s'" % k for k in bound_variables) + "]"            
            return_dict_expr_src = "{{k: __locals[k] for k in {return_dict_list_src} if k in __locals}}".format(
                return_dict_list_src=return_dict_list_src)
            return_dict_expr_src = "(lambda __locals: {return_dict_expr_src})(dict(locals()))".format(
                return_dict_expr_src=return_dict_expr_src)

            return_dict_expr = ast.parse(return_dict_expr_src).body[0].value

            return_statement = ast.Return(
                    ast.Tuple([
                        return_dict_expr,
                        ast.Num(0),
                        ast.Num(0)
                        ],
                    ast.Load()
                    )
                )

            return_statement_exception = ast.Return(
                    ast.Tuple([
                        return_dict_expr,
                        ast.Call(ast.Name("__pyfora_get_exception_traceback__", ast.Load()), [],[],None,None),
                        ast.Name("__pyfora_exception_var__", ast.Load())
                        ],
                    ast.Load()
                    )
                )

            expr.body.append(return_statement)

            handler = ast.ExceptHandler(None, ast.Name("__pyfora_exception_var__", ast.Store()), [return_statement_exception])

            #now wrap in a try-catch block
            curBody = list(expr.body)
            expr.body = [ast.TryExcept(curBody, [handler], [])]

            #for every incoming variable 'x' that's also assigned to, create a dummy '__pyfora_var_guard_x' that actually
            #takes the value in from the surrounding scope, and immediately assign it
            for var in memberDictionary:
                if var in bound_variables:
                    newVar = "__pyfora_var_guard_" + var

                    var_copy_expr = ast.Assign(
                        targets=[ast.Name(var, ast.Store())],
                        value=ast.Name(newVar, ast.Load())
                        )

                    globalScope[newVar] = globalScope[var]
                    del globalScope[var]

                    expr.body = [var_copy_expr] + expr.body

            expr = updatePyAstMemberChains(
                expr,
                tuple(globalScope.keys()),
                isClassContext=True)

            ast.fix_missing_locations(expr)

            def extractTrace():
                return sys.exc_info()[2]

            globalScope['__pyfora_get_exception_traceback__'] = extractTrace

            code = compile(ast.Module([expr]), filename, 'exec')

            exec code in globalScope, outputLocals
            assert len(outputLocals) == 1
            return list(outputLocals.values())[0]
        else:
            functionAst = updatePyAstMemberChains(
                ast.Module(
                    [functionAst],
                    lineno=1,col_offset=0),
                tuple(globalScope.keys()),
                isClassContext=False)

            code = compile(functionAst, filename, 'exec')

            exec code in globalScope, outputLocals
            assert len(outputLocals) == 1
            return list(outputLocals.values())[0]

