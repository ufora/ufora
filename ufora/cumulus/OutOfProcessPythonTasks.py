import ufora.native.Cumulus as CumulusNative
import pyfora.worker.WorkerPool as WorkerPool
import pyfora.NamedSingletons as NamedSingletons
import ufora.FORA.python.PurePython.Converter as Converter
import pyfora.PyAbortSingletons as PyAbortSingletons
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter
import ufora.FORA.python.ModuleImporter as ModuleImporter
import tempfile

def constructNativeTasksObject(pathToSocketDir):
    pythonNameToPyforaName = {}

    pythonNameToPyforaName.update(
        NamedSingletons.pythonNameToPyforaName
        )

    pythonNameToPyforaName.update(
        PyAbortSingletons.pythonNameToPyforaName
        )

    return CumulusNative.OutOfProcessPythonTasks(
        pythonNameToPyforaName,
        Converter.canonicalPurePythonModule(),
        ModuleImporter.builtinModuleImplVal(),
        PythonAstConverter.parseStringToPythonAst,
        pathToSocketDir
        )

class OutOfProcessPythonTasks:
    def __init__(self, pathToSocketDir=None, outOfProcess=True):
        if pathToSocketDir is None:
            pathToSocketDir = tempfile.mkdtemp()

        self.pathToSocketDir = pathToSocketDir
        
        self.workerPool = WorkerPool.WorkerPool(pathToSocketDir, outOfProcess=outOfProcess, max_processes = 30)
        self.workerPool.blockUntilConnected()

        self.nativeTasks = constructNativeTasksObject(pathToSocketDir)

    def teardown(self):
        self.workerPool.terminate()

