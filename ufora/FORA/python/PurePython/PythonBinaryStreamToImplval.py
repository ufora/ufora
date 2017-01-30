import ufora.native.FORA as ForaNative
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyAbortSingletons as PyAbortSingletons
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter
import ufora.FORA.python.ModuleImporter as ModuleImporter

def constructConverter(purePythonModuleImplVal, vdm):
    pythonNameToPyforaName = {}
    
    pythonNameToPyforaName.update(
        NamedSingletons.pythonNameToPyforaName
        )
    pythonNameToPyforaName.update(
        PyAbortSingletons.pythonNameToPyforaName
        )

    return ForaNative.PythonBinaryStreamToImplval(
        vdm,
        purePythonModuleImplVal,
        ModuleImporter.builtinModuleImplVal(),
        pythonNameToPyforaName,
        PythonAstConverter.parseStringToPythonAst
        )
