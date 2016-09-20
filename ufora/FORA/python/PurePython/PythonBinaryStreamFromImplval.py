import ufora.native.FORA as ForaNative
import ufora.FORA.python.PurePython.Converter as Converter

def constructConverter(purePythonModuleImplVal, vdm):
    converter = Converter.constructConverter(purePythonModuleImplVal, vdm)

    return ForaNative.PythonBinaryStreamFromImplval(
        vdm,
        purePythonModuleImplVal,
        converter.nativeConstantConverter,
        converter.nativeListConverter,
        converter.nativeTupleConverter,
        converter.nativeDictConverter,
        ForaNative.PyforaSingletonAndExceptionConverter(
            converter.purePythonModuleImplVal,
            converter.singletonAndExceptionConverter.pythonNameToInstance
            )
        )
