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

import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.ForaValue as ForaValue
import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaToJsonTransformer \
    as PyforaToJsonTransformer

from pyfora.Exceptions import PythonToForaConversionError

import ufora.native.FORA as ForaNative

import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.PyAstUtil as PyAstUtil
from pyfora.ObjectVisitors import walkPythonObject

import unittest

class DirectPyforaConverterTest(unittest.TestCase):
    def setUp(self):
        self.converter = Converter.Converter(
            vdmOverride=ForaValue.evaluator().getVDM()
            )
        self.objectRegistry = ObjectRegistry.ObjectRegistry()

    def convertPyObjectToImplVal(self, pyObject):
        objectId = walkPythonObject(pyObject, self.objectRegistry)

        implVal = [None]
        def onResult(result):
            if isinstance(result, Exception):
                raise result
            else:
                implVal[0] = result

        self.converter.convert(objectId, self.objectRegistry, onResult)
        return implVal[0]


    def checkFunctionEquivalence(self, pyFunction, valuesToCheck=None):
        functionImplVal = self.convertPyObjectToImplVal(pyFunction)

        self.assertIsInstance(functionImplVal, ForaNative.ImplValContainer)

        functionForaValue = ForaValue.FORAValue(functionImplVal)

        if valuesToCheck is None:
            self.assertEqual(
                pyFunction(),
                functionForaValue()
                )
        else:
            for valueToCheck in valuesToCheck:
                self.assertEqual(
                    pyFunction(valueToCheck),
                    functionForaValue(valueToCheck)
                    )

    def test_primitives_1(self):
        x = 1

        implVal = self.convertPyObjectToImplVal(x)

        self.assertIsInstance(implVal, ForaNative.ImplValContainer)
        self.assertEqual(implVal.pyval, x)

    def test_functions_1(self):
        def f(x):
            return x + 1

        self.checkFunctionEquivalence(f, [1,2,3])

    def test_functions_2(self):
        y = 3
        def f(x):
            return x + y

        self.checkFunctionEquivalence(f, [1,2,3])

    def test_functions_3(self):
        y = 3
        def f(x):
            return x + y
        z = 4
        def g(x):
            return x + f(x) + z

        self.checkFunctionEquivalence(g, [4,5,6])

    def test_functions_4(self):
        def f(x):
            if x < 0:
                return x
            return x + g(x - 1)
        def g(x):
            if x < 0:
                return x
            return x * f(x - 1)

        self.checkFunctionEquivalence(f, range(10))

    def test_functions_mutual_recursion_across_modules(self):
        import ufora.FORA.python.PurePython.testModules.MutualRecursionAcrossModules.A as A

        self.checkFunctionEquivalence(A.f, range(4))

    def test_functions_5(self):
        def f(x):
            def g():
                return 1 + x
            return g()

        self.checkFunctionEquivalence(f, [-3,-2,-1])

    def test_functions_6(self):
        def h(x):
            return 2 * x
        def f(x):
            if x < 0:
                return x
            return g(x - 1) + h(x)
        def g(x):
            if x < 0:
                return x
            return f(x - 1) + h(x - 1)

        self.checkFunctionEquivalence(f, range(10))

    def test_functions_7(self):
        w = 3
        def h(x):
            return w + 2 * x
        def f(x):
            if x < 0:
                return x
            return g(x - 1) + h(x)
        def g(x):
            if x < 0:
                return x
            return f(x - 1) + h(x - 1)

        self.checkFunctionEquivalence(f, range(10))

    def test_functions_8(self):
        y = 1
        z = 2
        w = 3
        def h(x):
            return w + 2 * x
        def f(x):
            if x < 0:
                return x
            return y + g(x - 1) + h(x)
        def g(x):
            if x < 0:
                return x
            return z * f(x - 1) + h(x - 1)

        self.checkFunctionEquivalence(f, range(10))

    def test_functions_9(self):
        y = 2
        def h(x, fn):
            if x < 0:
                return x
            return x + y * fn(x - 1)
        def f(x):
            def g(arg):
                if arg < 0:
                    return x + arg
                return x * h(arg - 1, g)
            return g

        self.checkFunctionEquivalence(f(3), range(10))

    def test_functions_10(self):
        x = 2
        y = 3
        def f():
            return x + g()
        def g():
            return y + f() + h()
        def h():
            pass

        # chek these doesn't blow up
        self.convertPyObjectToImplVal(f)
        self.convertPyObjectToImplVal(g)
        self.convertPyObjectToImplVal(h)

    def test_classes_1(self):
        class C1:
            def __init__(self, x):
                self.x = x
            def f(self, arg):
                return self.x + arg

        ivc = self.convertPyObjectToImplVal(C1)
        foraValue = ForaValue.FORAValue(ivc)

        x = 2
        foraClassInstance = foraValue(x)

        arg = 3
        self.assertEqual(foraClassInstance.f(arg), C1(x).f(arg))

    def test_classes_2(self):
        a = 2
        def func_1(arg):
            return arg + a
        class C2:
            def __init__(self, x):
                self.x = x
            def func_2(self, arg):
                return self.x + func_1(arg)

        ivc = self.convertPyObjectToImplVal(C2)

        foraValue = ForaValue.FORAValue(ivc)

        x = 2
        foraClassInstance = foraValue(x)

        arg = 3
        self.assertEqual(foraClassInstance.func_2(arg), C2(x).func_2(arg))

    @unittest.skip("@staticmethod trips PyObjectWalker")
    def test_classes_3(self):
        class C3:
            @staticmethod
            def g(x):
                return x + 1

        ivc = self.convertPyObjectToImplVal(C3)

        foraClass = ForaValue.FORAValue(ivc)

        arg = 10
        self.assertEqual(foraClass.g(arg), C3.g(arg))

    def test_class_instances_1(self):
        class C4:
            def __init__(self, x, y):
                self.x = x
                self.y = y
                self.z = x + y
            def f(self, arg):
                return arg + self.x + self.y + self.z

        pyObject = C4(100, 200)

        ivc = self.convertPyObjectToImplVal(pyObject)
        foraValue = ForaValue.FORAValue(ivc)

        arg = 10
        self.assertEqual(foraValue.f(arg), pyObject.f(arg))

        classIvc = self.convertPyObjectToImplVal(C4)

        nativeDataMembers = classIvc.getDataMembers
        pyDataMembers = PyAstUtil.computeDataMembers(C4)

        for memberName in ['x', 'y', 'z']:
            self.assertEqual(
                getattr(pyObject, memberName),
                getattr(foraValue, memberName)
                )

    def test_class_instances_2(self):
        class C5:
            def __init__(self, x):
                self.x = x
            def f(self, y):
                return self.x + y

        pyObject = C5(42)

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyObject)
            )

        arg = 10
        self.assertEqual(foraValue.f(arg), pyObject.f(arg))
        self.assertEqual(foraValue.x, pyObject.x)

    def test_class_instances_3(self):
        class C6:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        pyObject = C6(1, 2)

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyObject)
            )

        self.assertEqual(foraValue.x, pyObject.x)
        self.assertEqual(foraValue.y, pyObject.y)

    def test_class_instances_4(self):
        class C7:
            def __init__(self, x, y):
                self.y = y
                self.x = x

        pyObject = C7(1, 2)

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyObject)
            )

        self.assertEqual(foraValue.x, pyObject.x)
        self.assertEqual(foraValue.y, pyObject.y)

    def test_class_instances_5(self):
        class C8:
            def __init__(self, x):
                self.x = x

            def f(self, arg):
                if arg <= 0:
                    return self.x
                return arg * self.g(arg - 1)

            def g(self, arg):
                if arg <= 0:
                    return -self.x
                return arg + self.f(arg - 2)

        pyObject = C8(10)

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyObject)
            )

        self.assertEqual(pyObject.x, foraValue.x)

        for arg in range(10):
            self.assertEqual(pyObject.f(arg), foraValue.f(arg))

    @unittest.skip("@staticmethod trips PyObjectWalker")
    def test_class_instances_6(self):
        def f(x):
            if x < 0:
                return x
            return g(x - 1)
        def g(x):
            if x < 0:
                return x
            return f(x - 2)
        class C9:
            def __init__(self, x, c):
                self.x = x
                self.c = c
            @staticmethod
            def staticfunc(x):
                return f(x)
            def memberfunc(self, arg):
                return f(self.x) + self.c.x + arg

        pyObject = C9(x=12, c=C9(42, 1337))

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyObject)
            )

        self.assertEqual(pyObject.x, foraValue.x)

        for arg in range(10):
            self.assertEqual(pyObject.memberfunc(arg), foraValue.memberfunc(arg))

    @unittest.skip("@staticmethod trips PyObjectWalker")
    def test_class_instances_7(self):
        class C10:
            @staticmethod
            def g(x):
                return x + 1
            def f(self, arg):
                return C10.g(arg)

        pyObject = C10()

        ivc = self.convertPyObjectToImplVal(pyObject)
        foraValue = ForaValue.FORAValue(ivc)

        arg = 3
        self.assertEqual(pyObject.f(arg), foraValue.f(arg))

    @unittest.skip("@staticmethod trips PyObjectWalker")
    def test_freeVariablesInClasses_1(self):
        x = 42
        class C11:
            @staticmethod
            def f1(x):
                return x
            @staticmethod
            def f2(arg):
                return x + arg
            def f3(self, arg):
                return x + arg
            def f4(self, x):
                return x

        foraClass = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(C11)
            )

        self.assertEqual(C11.f1(0), foraClass.f1(0))
        self.assertEqual(C11.f2(1), foraClass.f2(1))

        c = C11()

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(c)
            )

        self.assertEqual(c.f3(1), foraValue.f3(1))
        self.assertEqual(c.f4(1), foraValue.f4(1))

    def test_freeVariablesInClasses_2(self):
        class C12:
            def __init__(self, x):
                self.x = x

        c8 = C12(42)
        class C13:
            def f(self, arg):
                if arg < 0:
                    return 0
                return c8.x + self.g(arg - 1)
            def g(self, arg):
                if arg < 0:
                    return arg
                return c8.x * self.f(arg - 2)

        c = C13()

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(c)
            )

        for ix in range(10):
            self.assertEqual(c.f(ix), foraValue.f(ix))
            self.assertEqual(c.g(ix), foraValue.g(ix))

    @unittest.skip("@staticmethod trips PyObjectWalker")
    def test_freeVariablesInClasses_4(self):
        class C_freeVars_4_1:
            @staticmethod
            def f(x):
                return x + 1

        class C_freeVars_4_2:
            def g(self, arg):
                if arg < 0:
                    return 0
                return C_freeVars_4_1.f(arg) + self.h(arg - 1)
            def h(self, arg):
                if arg < 0:
                    return arg
                return C_freeVars_4_1.f(arg) * self.g(arg - 2)

        c = C_freeVars_4_2()

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(c)
            )

        for ix in range(10):
            self.assertEqual(c.h(ix), foraValue.h(ix))
            self.assertEqual(c.g(ix), foraValue.g(ix))

    def test_freeVariablesInClasses_5(self):
        class C_freeVars_5_1:
            def f(self, x):
                return x + 1

        c = C_freeVars_5_1()
        class C_freeVars_5_2:
            def f(self, arg):
                if arg < 0:
                    return 0
                return c.f(arg) + self.g(arg - 1)
            def g(self, arg):
                if arg < 0:
                    return arg
                return c.f(arg) * self.f(arg - 2)

        c2 = C_freeVars_5_2()

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(c2)
            )

        for ix in range(10):
            self.assertEqual(c2.f(ix), foraValue.f(ix))
            self.assertEqual(c2.g(ix), foraValue.g(ix))

    def test_freeVariablesInClasses_6(self):
        x = 2
        class C_freeVars_6_1:
            def f(self):
                return x

        c = C_freeVars_6_1()

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(c)
            )

        self.assertEqual(c.f(), foraValue.f())

    def test_freeVariablesInClasses_7(self):
        class C_freeVars_7_1:
            def f(self, arg):
                return arg + 1

        c = C_freeVars_7_1()
        def f(x):
            return c.f(x)

        foraFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        arg = 10
        self.assertEqual(f(arg), foraFunction(arg))


    def test_lists_1(self):
        pyObject = [1,2,3,4]

        ivc = self.convertPyObjectToImplVal(pyObject)
        foraValue = ForaValue.FORAValue(ivc)

        for ix in range(-len(pyObject), len(pyObject)):
            self.assertEqual(
                pyObject[ix],
                foraValue[ix]
                )

    def test_lists_2(self):
        class C_lists:
            def __init__(self, x):
                self.x = x

        pyObject = [1,2,3,C_lists(3)]

        ivc = self.convertPyObjectToImplVal(pyObject)
        foraValue = ForaValue.FORAValue(ivc)

        for ix in [-4,-3,-2,0,1,2]:
            self.assertEqual(
                pyObject[ix],
                foraValue[ix]
                )

        self.assertEqual(
            pyObject[-1].x,
            foraValue[-1].x
            )

        self.assertEqual(
            pyObject[3].x,
            foraValue[3].x
            )

    def test_classes_with_getitems(self):
        class C_with_getitem:
            def __init__(self, m):
                self.__m__ = m

            def __getitem__(self, ix):
                return self.__m__[ix]

        size = 10
        pyObject = C_with_getitem(range(10))

        ivc = self.convertPyObjectToImplVal(pyObject)
        foraValue = ForaValue.FORAValue(ivc)

        for ix in range(size):
            self.assertEqual(
                pyObject[ix],
                foraValue[ix]
                )
            self.assertEqual(
                pyObject.__getitem__(ix),
                foraValue.__getitem__(ix)
                )

    def test_lists_with_circular_references_1(self):
        circularList = [1,2,3]
        circularList.append(circularList)

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(circularList)

    def test_lists_with_circular_references_2(self):
        circularList = [1,2,3]
        class SomeClass1:
            def __init__(self, val):
                self.__m__ = val
        circularList.append(SomeClass1(circularList))

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(circularList)

    def test_lists_with_circular_references_3(self):
        circularList = [1,2,3]
        class SomeClass2:
            def __init__(self, val):
                self.__m__ = val
        circularList.append(
            SomeClass2(
                SomeClass2(
                    [circularList, 2]
                    )
                )
            )

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(circularList)

    def test_tuples_1(self):
        tup = (1, 2, 3)

        foraValue = ForaValue.FORAValue(self.convertPyObjectToImplVal(tup))

        for ix in range(-3, 3):
            self.assertEqual(
                tup[ix],
                foraValue[ix]
                )

    def test_mutuallyRecursiveModuleMembers_1(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers1 \
            as MutuallyRecursiveModuleMembers1

        pythonInt = 2
        expectedResult = MutuallyRecursiveModuleMembers1.f(pythonInt)

        implValFunction = self.convertPyObjectToImplVal(
            MutuallyRecursiveModuleMembers1.f
            )
        foraValueFunction = ForaValue.FORAValue(implValFunction)

        implValInt = self.convertPyObjectToImplVal(pythonInt)
        foraValueInt = ForaValue.FORAValue(implValInt)

        self.assertEqual(
            foraValueFunction(foraValueInt),
            expectedResult
            )

    def test_mutuallyRecursiveModuleMembers_2(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers2 \
            as MutuallyRecursiveModuleMembers2

        callingValue = 3
        expectedResult = MutuallyRecursiveModuleMembers2.f4(callingValue)

        implValFunction = self.convertPyObjectToImplVal(
            MutuallyRecursiveModuleMembers2.f4
            )
        foraValueFunction = ForaValue.FORAValue(implValFunction)

        implValInt = self.convertPyObjectToImplVal(callingValue)
        foraValueInt = ForaValue.FORAValue(implValInt)

        self.assertEqual(
            foraValueFunction(foraValueInt),
            expectedResult
            )

    def test_mutuallyRecursiveModuleMembers_3(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers3 \
            as MutuallyRecursiveModuleMembers1

        callingValue = 3
        expectedResult = MutuallyRecursiveModuleMembers1.f(callingValue)

        implValFunction = self.convertPyObjectToImplVal(
            MutuallyRecursiveModuleMembers1.f
            )
        foraValueFunction = ForaValue.FORAValue(implValFunction)

        implValInt = self.convertPyObjectToImplVal(callingValue)
        foraValueInt = ForaValue.FORAValue(implValInt)

        self.assertEqual(
            foraValueFunction(foraValueInt),
            expectedResult
            )

    def test_closures_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures1 \
            as ModuleWithClosures1

        pyInts = (3, 4)
        expectedResult = ModuleWithClosures1.f1(*pyInts)

        implValFunction = self.convertPyObjectToImplVal(
            ModuleWithClosures1.f1
            )
        foraValueFunction = ForaValue.FORAValue(implValFunction)

        foraValueInts = [ForaValue.FORAValue(
                self.convertPyObjectToImplVal(pyInt)
                ) for pyInt in pyInts]

        self.assertEqual(
            expectedResult,
            foraValueFunction(*foraValueInts)
            )

    def test_closures_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures2 \
            as ModuleWithClosures2

        pyInts = (3, 4)
        expectedResult = ModuleWithClosures2.f1(*pyInts)

        implValFunction = self.convertPyObjectToImplVal(
            ModuleWithClosures2.f1
            )
        foraValueFunction = ForaValue.FORAValue(implValFunction)

        foraValueInts = [ForaValue.FORAValue(
                self.convertPyObjectToImplVal(pyInt)
                ) for pyInt in pyInts]

        self.assertEqual(
            expectedResult,
            foraValueFunction(*foraValueInts)
            )

    def test_imports_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithImport \
            as ModuleWithImport

        pyInt = 2
        expectedResult = ModuleWithImport.h(pyInt)

        foraValueFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(
                ModuleWithImport.h
                )
            )

        foraValueInt = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyInt)
            )

        self.assertEqual(
            expectedResult,
            foraValueFunction(foraValueInt)
            )

    def test_imports_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithOneMember \
            as ModuleWithOneMember

        def f(x):
            return ModuleWithOneMember.h(x)

        pyInt = 2
        expectedResult = f(pyInt)

        foraValueFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        foraValueInt = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyInt)
            )

        self.assertEqual(expectedResult, foraValueFunction(foraValueInt))

    def test_imports_3(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithUnconvertableMember \
            as ModuleWithUnconvertableMember

        def f(x):
            return ModuleWithUnconvertableMember.convertableMember(x)

        def unconvertable(x):
            return ModuleWithUnconvertableMember.unconvertableMember(x)

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(unconvertable)

        pyInt = 2
        expectedResult = f(pyInt)

        foraValueFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )
        foraValueInt = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyInt)
            )

        self.assertEqual(expectedResult, foraValueFunction(foraValueInt))

    def test_functionsWithTheSameName(self):
        # inspect, from the python std library, which we use,
        # does the right thing for functions.
        # the corresponding test for classes fails
        def f1():
            def f():
                return 1
            return f
        def f2():
            def f():
                return -1
            return f

        func1 = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f1())
            )
        func2 = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f2())
            )

        self.assertEqual(func1(), 1)
        self.assertEqual(func2(), -1)

    def test_initMethods_1(self):
        class A1():
            def __init__(self):
                class B():
                    pass                

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(A1)

    def test_initMethods_2(self):
        class A2():
            def __init__(self):
                def foo():
                    pass

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(A2)

    def test_initMethods_3(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x + arg
            return A(2).x

        foraValueFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        for ix in range(-10, 10):
            self.assertEqual(
                foraValueFunction(ix),
                f(ix)
                )

    def test_initMethods_4(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self_x = arg
                    self.x = x + self_x
            return A(2).x

        self.checkFunctionEquivalence(f, range(4))

    def test_initMethods_5(self):
        def f():
            class A():
                def __init__(self, x):
                    self = 2
                    self.x = x
            return A


        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(f)

    def test_initMethods_6(self):
        def f():
            class A():
                def __init__(self, x):
                    (self.x, self.y) = (x, x + 1)
            return A(2).x

        with self.assertRaises(PythonToForaConversionError):
            self.convertPyObjectToImplVal(f)

    def test_initMethods_7(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x
                    self.y = self.x + 1
            return A(arg).x

        self.checkFunctionEquivalence(f, range(4))

    def test_initMethods_8(self):
        def f(arg):
            class A():
                def __init__(selfArg):
                    selfArg.x = 2
                    selfArg.x = selfArg.x + 1
            return A().x + arg

        self.checkFunctionEquivalence(f, range(4))

    def test_initMethods_9(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x
                    self.x = self.x + 1
                def foo(self, y):
                    return self.x + y

            return A(arg).foo(2)

        self.checkFunctionEquivalence(f, range(4))

    def test_initMethods_10(self):
        def f(_):
            class A():
                def __init__(selfArg, x):
                    if x > 0:
                        selfArg.x = x
                    else:
                        selfArg.x = -x

            return A(1).x + A(-1).x

        self.checkFunctionEquivalence(f, range(-4,1))

    def test_recursiveFunctions_1(self):
        def fact(n):
            if n == 0:
                return 1
            return n * fact(n - 1)

        self.checkFunctionEquivalence(fact, range(5))

    def test_recursiveFunctions_2(self):
        def fib(n):
            if n <= 1:
                return n

            return fib(n - 1) + fib(n - 2)

        self.checkFunctionEquivalence(fib, range(5))

    def test_nestedLists_1(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.checkFunctionEquivalence(nestedLists)

    def test_inStatement_1(self):
        def inStatement():
            x = [0,1,2,3]
            return 0 in x

        self.checkFunctionEquivalence(inStatement)

    def test_iteration_1(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.checkFunctionEquivalence(iteration_1)

    def test_pass(self):
        def passStatement():
            def f():
                pass

            x = f()
            return x

        self.checkFunctionEquivalence(passStatement)

    def test_returningTuples_1(self):
        def returningATuple_1():
            return (0, 1)

        self.checkFunctionEquivalence(returningATuple_1)

    def test_returningTuples_2(self):
        def returningATuple_2():
            return 0, 1

        self.checkFunctionEquivalence(returningATuple_2)

    def test_nestedComprehensions_1(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.checkFunctionEquivalence(nestedComprehensions)

    def test_listComprehensions_1(self):
        def listComprehensions_1(arg):
            aList = [0,1,2,3]
            aList = [elt ** 2 for elt in aList]
            return aList[arg]

        self.checkFunctionEquivalence(listComprehensions_1, range(-4, 4))

    def test_listComprehensions_2(self):
        def listComprehensions_2(arg):
            aList = [0,1,2,3]
            return [elt for elt in aList if elt % 2 == 0][arg]

        self.checkFunctionEquivalence(listComprehensions_2, range(-2, 2))

    def test_listComprehensions_3(self):
        def listComprehensions_3(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[arg]

        self.checkFunctionEquivalence(listComprehensions_3, range(-9, 9))

    def test_listComprehensions_4(self):
        def listComprehensions_4(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]
            return aList[arg]

        self.checkFunctionEquivalence(listComprehensions_4, range(-7, 7))

    def test_basicAddition(self):
        def basicAddition(x):
            return x + 1

        self.checkFunctionEquivalence(basicAddition, [4])

    def test_argumentAssignment(self):
        def argumentAssignment(x):
            x = x + 1
            return x

        self.checkFunctionEquivalence(argumentAssignment, [100])

    def test_variableAssignment(self):
        def variableAssignment(x):
            y = x + 1
            return x+y

        self.checkFunctionEquivalence(variableAssignment, range(3))

    def test_whileLoop(self):
        def whileLoop(x):
            y = 0
            while x < 100:
                y = y + x
                x = x + 1
            return y

        self.checkFunctionEquivalence(whileLoop, range(4))

    def test_isPrime(self):
        def isPrime(p):
            x = 2
            while x * x <= p:
                if p % x == 0:
                    return 0
                x = x + 1
            return 0

        self.checkFunctionEquivalence(isPrime, range(10))

    def test_lambdaFunction(self):
        def lambdaFunction(x):
            z = lambda y: x + y
            return z(10)

        self.checkFunctionEquivalence(lambdaFunction, range(4))

    def test_inlineFunction(self):
        def inlineFunction(x):
            def z(y):
                return x+y
            return z(10)

        self.checkFunctionEquivalence(inlineFunction, range(4))

    def test_basicLists_1(self):
        def basicLists(x):
            aList = [x] + [x]
            return aList[0] + aList[1]

        self.checkFunctionEquivalence(basicLists, [3])

    def test_loopsum(self):
        def loopSum(x):
            y = 0
            while x > 0:
                y = y + x
                x = x - 1
            return y

        self.checkFunctionEquivalence(loopSum, range(3))

    def test_loopsAndYields(self):
        def loopsAndYields(x):
            def sequence(x):
                y = 0
                while y < x:
                    yield y
                    y = y + 1

            res = 0
            for val in sequence(x):
                res = res + val
            return res

        self.checkFunctionEquivalence(loopsAndYields, range(5))

    def test_implicitReturnNone_1(self):
        def f():
            x = 2

        foraFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        self.assertEqual(f(), foraFunction())

    def test_implicitReturnNone_2(self):
        def f(x):
            x

        foraFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        arg = 10
        self.assertEqual(f(arg), foraFunction(arg))

    def test_implicitReturnNone_3(self):
        def f(x):
            if x > 0:
                return
            else:
                return 1

        foraFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        arg = 1
        self.assertEqual(f(arg), foraFunction(arg))

        arg = -1
        self.assertEqual(f(arg), foraFunction(arg))

    def test_ints_1(self):
        x = 42

        self.assertEqual(
            self.convertPyObjectToImplVal(x).pyval,
            x
            )

    def test_bools_1(self):
        x = True

        self.assertEqual(
            self.convertPyObjectToImplVal(x).pyval,
            x
            )

    def test_floats_1(self):
        x = 42.0

        self.assertEqual(
            self.convertPyObjectToImplVal(x).pyval,
            x
            )

    def test_strings_1(self):
        x = "asdf"

        self.assertEqual(
            self.convertPyObjectToImplVal(x).pyval,
            x
            )

    def test_dicts_1(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(x)
            )

        for key in x:
            self.assertEqual(
                foraValue[key],
                x[key]
                )

    def test_dicts_2(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f():
            return x

        ivc = self.convertPyObjectToImplVal(f)

        transformer = PyforaToJsonTransformer.PyforaToJsonTransformer()

        self.converter.transformPyforaImplval(ivc, transformer, None)

        

