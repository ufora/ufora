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

# ideas used from withhacks, python library: https://github.com/rfk/withhacks
"""
WithBlockExecutor

Extracts the Python code nested in its code-block and automatically sends 
that code as a callable to the Ufora cluster
"""

import traceback
import logging
import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions
import pyfora.PyAstUtil as PyAstUtil
import pyfora.DownloadPolicy as DownloadPolicy
import sys
import pyfora.PyforaWithBlock as PyforaWithBlock
import ast


INNER_FUNCTION_NAME = 'inner'

class AugmentRaiseFunctionModificationVisitor(ast.NodeVisitor):
    """Takes a line number, column number, and function name updates the AST.

    All nodes that have a 'lineno' attribute have their lineno and col attributes
    set, and any identifier (in FunctionDef or Name nodes) whose text is
    'INNER_FUNCTION_NAME' is replaced with the provided function name."""
    def __init__(self, line, col, functionName = None):
        self.line = line
        self.col = col
        self.functionName = functionName

    def generic_visit(self, node):
        super(AugmentRaiseFunctionModificationVisitor, self).generic_visit(node)
        if hasattr(node, PyAstUtil.LINENO_ATTRIBUTE_NAME):
            node.lineno = self.line
            node.col_offset = self.col

        if isinstance(node, ast.FunctionDef) and node.name == INNER_FUNCTION_NAME and \
                self.functionName is not None:
            node.name = self.functionName
        if isinstance(node, ast.Name) and node.id == INNER_FUNCTION_NAME and \
                self.functionName is not None:
            node.id = self.functionName

augmentRaiseFunctionTemplate = """
def _augmentRaiseFunctionTempl(rf):
    def """ + INNER_FUNCTION_NAME + """():
        if rf is None:
            raise Exception()
        else:
            rf()
    return """ + INNER_FUNCTION_NAME

def augmentRaiseFunction(raiseFunction, path, line, col):
    enclosingFunctionVisitor = PyAstUtil.FindEnclosingFunctionVisitor(line)
    codeAst = PyAstUtil.getAstFromFilePath(path)
    enclosingFunctionName = enclosingFunctionVisitor.find(codeAst)
    vis = AugmentRaiseFunctionModificationVisitor(line, col, enclosingFunctionName)
    module = ast.parse(augmentRaiseFunctionTemplate)
    vis.visit(module)

    code = compile(module, path, 'exec')
    exec code in globals(), locals()

    return _augmentRaiseFunctionTempl(raiseFunction)

def syntheticTraceback(trace):
    raiseFunction = None

    for elt in trace:
        if len(elt['path']) == 1 and (elt['path'][0].endswith(".py") or elt['path'][0].endswith(".pyc")):
            raiseFunction = augmentRaiseFunction(
                raiseFunction,
                elt['path'][0],
                elt['range']['start']['line'],
                elt['range']['start']['col']
                )

    try:
        raiseFunction()
    except:
        return sys.exc_info()[2].tb_next

class WithBlockExecutor(object):
    """
    will extract python code from a with block and submit that code 
    to the ufora cluster for remote execution. Results of the remote 
    execution are returned as RemotePythonObject and are automatically 
    reasigned to their corresponding local variables in the with block.

    use downloadAll(), remoteAll() and downloadSmall() to modify the 
    behavior of the executor and set which objects should be download 
    from the server and which objects should be returned as 
    RemotePythonObject futures.
    """
    def __init__(self, executor):
        self.executor = executor
        self.lineNumber = None
        self.sourceText = None
        self.stackFrame = None
        self.sourceFileName = None
        self.traceAndException = None
        self.frame = None
        self.downloadPolicy = DownloadPolicy.DownloadNonePolicy()

    def downloadAll(self):
        """Modify the executor to download all results into the local namespace and return 'self' allowing chaining."""
        self.downloadPolicy = DownloadPolicy.DownloadAllPolicy()
        return self

    def remoteAll(self):
        """Modify the executor to leave all results on the server and only return proxies (default)."""
        self.downloadPolicy = DownloadPolicy.DownloadNonePolicy()
        return self

    def downloadSmall(self, bytecount=10*1000):
        """Modify the executor to download small results into the local namespace and return proxies for everything else."""
        self.downloadPolicy = DownloadPolicy.DownloadSmallPolicy(bytecount)
        return self
        

    def __enter__(self):
        sourceFileName, lineNumber, _, _ = traceback.extract_stack(limit=2)[0]
        self.sourceFileName = sourceFileName
        self.lineNumber = lineNumber
        with open(sourceFileName, "r") as sourceFile:
            self.sourceText = sourceFile.read()

        # Seems to "turn on" tracing, otherwise setting 
        # frame.f_trace seems to have no effect
        # doesn't seem to have any effects outside of this with context.
        sys.settrace(lambda *args, **keys: None)

        self.frame = PyforaInspect.currentframe(1)
        self.frame.f_trace = self.trace

    def __exit__(self, excType, excValue, trace):
        return True

    def blockOperation(self, frame):
        boundVariables = {}
        boundVariables.update(frame.f_globals)
        boundVariables.update(frame.f_locals)

        withBlock = PyforaWithBlock.PyforaWithBlock(
            lineNumber=self.lineNumber,
            sourceText=self.sourceText,
            boundVariables=boundVariables,
            sourceFileName=self.sourceFileName
            )

        f_proxy = self.executor.define(withBlock).result()

        f_result_proxy = f_proxy().result()

        tuple_of_proxies = f_result_proxy.toTupleOfProxies().result()

        proxy_trace = tuple_of_proxies[1]
        trace = proxy_trace.toLocal().result()

        if isinstance(trace, tuple):
            self.traceAndException = (trace, tuple_of_proxies[2].toLocal().result())

        proxy_dict = tuple_of_proxies[0]

        dict_of_proxies = proxy_dict.toDictOfAssignedVarsToProxyValues().result()

        return dict_of_proxies

    def trace(self, frame, event, arg):
        try:
            # It's very important not to write to frame.f_locals directly.
            # Apparently, each time we directly access the f_locals, member 
            # of a frame object, it calls some C code and syncs to its current
            # "internal" values. What we do instead is just read it out once,
            # at the beginning of the function, and then the writes will be seen later.
            # (see https://utcc.utoronto.ca/~cks/space/blog/python/FLocalsAndTraceFunctions
            # for a more full discussion, which led us to this approach)

            f_locals = frame.f_locals

            globalsToSet = self.blockOperation(frame)

            policyInstances = {}

            for keyname in list(globalsToSet.keys()):
                policyInstances[keyname] = self.downloadPolicy.initiatePolicyCheck(keyname, globalsToSet[keyname])

            for k, v in globalsToSet.iteritems():
                f_locals[k] = self.downloadPolicy.resolveToFinalValue(policyInstances[k])
        except Exceptions.PythonToForaConversionError as err:
            frame.f_lineno = frame.f_lineno-1
            raise err
        except Exceptions.ForaToPythonConversionError as err:
            frame.f_lineno = frame.f_lineno-1
            raise err
        except:
            logging.error("Exception in With-Block handler: %s", traceback.format_exc())

        if self.traceAndException is not None:
            exceptionValue = self.traceAndException[1]
            tb = syntheticTraceback(self.traceAndException[0])
            
            #setting the line number causes the trace to not call __exit__ and instead to
            #resume in the parent stackframe at the with block itself with the raised exception.
            #This causes the trace to contain two frames for the calling 'with' block, which is
            #not optimal, but it's better than the alternative which is to have the line-number
            #at the end of the 'with' block, which is just confusing.
            frame.f_lineno = frame.f_lineno-1
            raise exceptionValue, None, tb

        raise WithBlockCompleted()

class WithBlockCompleted(Exception):
    pass

