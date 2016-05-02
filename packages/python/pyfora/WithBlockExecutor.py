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
that code as a callable to the pyfora cluster
"""

import traceback
import logging
import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions
import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora.DownloadPolicy as DownloadPolicy
import sys
import pyfora.PyforaWithBlock as PyforaWithBlock
import ast

haveIPythonNotebook = False
try:
    import IPython
    if IPython.get_ipython() is not None:
        import IPython.core.display
        haveIPythonNotebook = True
except ImportError:
    pass


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
    codeAst = PyAstUtil.getAstFromFilePath(path)
    enclosingFunctionName = PyAstUtil.findEnclosingFunctionName(codeAst, line)
    vis = AugmentRaiseFunctionModificationVisitor(line, col, enclosingFunctionName)
    module = ast.parse(augmentRaiseFunctionTemplate)
    vis.visit(module)

    code = compile(module, path, 'exec')
    g = dict(globals())
    g['__file__'] = path
    exec code in g, locals()

    return _augmentRaiseFunctionTempl(raiseFunction)

def syntheticTraceback(trace):
    raiseFunction = None

    for elt in trace:
        path = elt['path']
        if len(path) == 1 and \
           (path[0].endswith(".py") or \
            path[0].endswith(".pyc") or \
            path[0].startswith("<ipython-input-")):
            raiseFunction = augmentRaiseFunction(
                raiseFunction,
                path[0],
                elt['range']['start']['line'],
                elt['range']['start']['col']
                )

    try:
        raiseFunction()
    except:
        return sys.exc_info()[2].tb_next

class WithBlockExecutor(object):
    """A helper object used to synchronously run blocks of code on a cluster.

    When entering a ``with`` block using a :class:`WithBlockExecutor`, the body of
    the block is extracted and submitted to the pyfora cluster for execution, along
    with all its local dependencies. Variable assignments within the block are
    returned as :class:`~RemotePythonObject.RemotePythonObject` and reassigned to
    their corresponding local varialbes when exiting the block.

    Use :func:`~WithBlockExecutor.downloadAll`, :func:`~WithBlockExecutor.remoteAll`,
    and :func:`~WithBlockExecutor.downloadSmall` to modify the default behavior and
    select which objects should be downloaded from the server and
    which objects should be returned as :class:`~RemotePythonObject.RemotePythonObject`
    futures.

    Note:
        Instances of :class:`WithBlockExecutor` are only intended to be created by
        :class:`~pyfora.Executor.Executor`. User code typically uses :attr:`~Executor.Executor.remotely`
        to get a :class:`WithBlockExecutor`.
    """
    def __init__(self, executor):
        self.executor = executor
        self.lineNumber = None
        self.sourceText = None
        self.stackFrame = None
        self.sourceFileName = None
        self.traceAndException = None
        self.frame = None
        self.compileOnly = False
        self.downloadPolicy = DownloadPolicy.DownloadNonePolicy()
        self.customComputationStatusCallback = None

    def asCompileOnly(self):
        self.compileOnly = True
        return self

    def withStatusCallback(self, callback):
        """Modify the executor to call 'callback' while computations are blocked with status updates.

        'callback' will receive a json package from the server containing information about the
        current computation. This will override the default callback, which attempts to determine
        whether we're in a jupyter notebook.
        """
        self.customComputationStatusCallback = callback
        return self

    def downloadAll(self):
        """Modify the executor to download all results into the local namespace.

        Returns:
            ``self`` to support chaining.
        """
        self.downloadPolicy = DownloadPolicy.DownloadAllPolicy()
        return self

    def remoteAll(self):
        """Modify the executor to leave all results on the server and only return proxies (default).

        Returns:
            ``self`` to support chaining.
        """
        self.downloadPolicy = DownloadPolicy.DownloadNonePolicy()
        return self

    def downloadSmall(self, bytecount=10*1000):
        """Modify the executor to download small results into the local namespace
        and return proxies for everything else.

        Returns:
            ``self`` to support chaining.
        """
        self.downloadPolicy = DownloadPolicy.DownloadSmallPolicy(bytecount)
        return self


    def __enter__(self):
        self.frame = PyforaInspect.currentframe(1)

        sourceFileName, lineNumber, _, _, _ = PyforaInspect.getframeinfo(self.frame)

        self.sourceFileName = sourceFileName
        self.lineNumber = lineNumber
        self.sourceText = "".join(PyforaInspect.getlines(self.sourceFileName))

        # Seems to "turn on" tracing, otherwise setting
        # frame.f_trace seems to have no effect
        # doesn't seem to have any effects outside of this with context.
        sys.settrace(lambda *args, **keys: None)

        self.frame.f_trace = self.trace

    def __exit__(self, excType, excValue, trace):
        # swallow WithBlockCompleted and let all other exceptions through
        return isinstance(excValue, WithBlockCompleted)

    def onComputationStatus(self, status):
        if self.customComputationStatusCallback is not None:
            self.customComputationStatusCallback(status)
        elif haveIPythonNotebook and IPython.get_ipython() is not None:
            IPython.core.display.clear_output(status is not None)
            if status is not None:
                IPython.core.display.display(
                    IPython.core.display.HTML("<div>Active Cores: %s</div>" % status['cpus']['value'])
                    )


    def blockOperation(self, frame):
        # variables bound in the enclosing context of the with-block frame.
        boundVariables = {}
        boundVariables.update(frame.f_globals)
        boundVariables.update(frame.f_locals)

        unboundLocals = []
        for var in frame.f_code.co_varnames:
            if var not in frame.f_locals:
                unboundLocals.append(var)
        unboundLocals = sorted(unboundLocals)

        withBlock = PyforaWithBlock.PyforaWithBlock(
            lineNumber=self.lineNumber,
            sourceText=self.sourceText,
            boundVariables=boundVariables,
            sourceFileName=self.sourceFileName,
            unboundLocals=unboundLocals
            )

        f_proxy = self.executor.define(withBlock).resultWithWakeup()

        if self.compileOnly:
            f_proxy.triggerCompilation().resultWithWakeup()
            return {}

        f_result_proxy = f_proxy().resultWithWakeup(self.onComputationStatus)

        try:
            tuple_of_proxies = f_result_proxy.toTupleOfProxies().resultWithWakeup()
        except Exceptions.ComputationError as e:
            self.traceAndException = (e.trace, e.remoteException)
            return {}

        proxy_trace = tuple_of_proxies[1]
        trace = proxy_trace.toLocal().resultWithWakeup()

        if isinstance(trace, tuple):
            self.traceAndException = (trace, tuple_of_proxies[2].toLocal().resultWithWakeup())

        proxy_dict = tuple_of_proxies[0]

        dict_of_proxies = proxy_dict.toDictOfAssignedVarsToProxyValues().resultWithWakeup()

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

            for k, _ in globalsToSet.iteritems():
                f_locals[k] = self.downloadPolicy.resolveToFinalValue(policyInstances[k])
        except (Exceptions.PythonToForaConversionError, Exceptions.ForaToPythonConversionError) as err:
            frame.f_lineno = frame.f_lineno - 1
            # re-raise to hide from users the traceback into the internals of pyfora
            logging.error("Re-raising exception to partially hide traceback.\n%s", traceback.format_exc())
            raise err
        except Exception:
            frame.f_lineno = frame.f_lineno - 1
            logging.error("Re-raising exception after amending lineno.\n%s", traceback.format_exc())
            raise

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

