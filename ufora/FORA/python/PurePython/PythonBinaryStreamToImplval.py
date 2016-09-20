import ufora.native.FORA as ForaNative
import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter

def constructConverter(purePythonModuleImplVal, vdm):
    converter = Converter.constructConverter(purePythonModuleImplVal, vdm)

    return ForaNative.PythonBinaryStreamToImplval(
        vdm,
        purePythonModuleImplVal,
        converter.builtinMemberMapping,
        converter.nativeConstantConverter,
        converter.nativeListConverter,
        converter.nativeTupleConverter,
        converter.nativeDictConverter,
        ForaNative.PyforaSingletonAndExceptionConverter(
            converter.purePythonModuleImplVal,
            converter.singletonAndExceptionConverter.pythonNameToInstance
            ),
        PythonAstConverter.parseStringToPythonAst
        )
