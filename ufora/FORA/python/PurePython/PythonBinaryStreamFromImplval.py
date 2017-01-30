import ufora.native.FORA as ForaNative
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyAbortSingletons as PyAbortSingletons

def constructConverter(purePythonModuleImplVal, vdm):
    pythonNameToPyforaName = {}
    
    pythonNameToPyforaName.update(
        NamedSingletons.pythonNameToPyforaName
        )
    pythonNameToPyforaName.update(
        PyAbortSingletons.pythonNameToPyforaName
        )

    return ForaNative.PythonBinaryStreamFromImplval(
        vdm,
        purePythonModuleImplVal,
        pythonNameToPyforaName
        )
