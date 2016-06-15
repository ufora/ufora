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


import ufora.FORA.python.PurePython.ConstantConverter as ConstantConverter

import pyfora

import ufora.native.FORA as ForaNative


Symbol_CreateInstance = ForaNative.makeSymbol("CreateInstance")


class NativeConverterAdaptor(object):
    def __init__(self,
                 nativeConstantConverter,
                 nativeDictConverter,
                 nativeTupleConverter,
                 nativeListConverter,
                 vdmOverride):
        self.constantConverter = ConstantConverter.ConstantConverter(
            nativeConstantConverter=nativeConstantConverter
            )
        self.nativeDictConverter = nativeDictConverter
        self.nativeTupleConverter = nativeTupleConverter
        self.nativeListConverter = nativeListConverter
        self.vdm_ = vdmOverride

    def createList(self, listOfConvertedValues):
        return self.nativeListConverter.createList(
            listOfConvertedValues,
            self.vdm_
            )

    def invertList(self, implval):
        return self.nativeListConverter.invertList(implval)

    def createListOfPrimitives(self, value):
        return self.nativeListConverter.createListOfPrimitives(
            value,
            self.constantConverter.nativeConstantConverter,
            self.vdm_
            )

    def convertConstant(self, value):
        return self.constantConverter.convert(value)

    def invertForaConstant(self, foraConstant):
        return self.constantConverter.invertForaConstant(foraConstant)

    def createTuple(self, listOfConvertedValues):
        return self.nativeTupleConverter.createTuple(listOfConvertedValues)

    def invertTuple(self, tupleIVC):
        return self.nativeTupleConverter.invertTuple(tupleIVC)

    def createDict(self, convertedKeysAndVals):
        return self.nativeDictConverter.createDict(convertedKeysAndVals)

    def invertDict(self, dictIVC):
        return self.nativeDictConverter.invertDict(dictIVC)

    def convertClassInstanceDescription(self, objectId, classInstanceDescription, convertedValues):
        classMemberNameToImplVal = {
            classMemberName: convertedValues[memberId]
            for classMemberName, memberId in
            classInstanceDescription.classMemberNameToClassMemberId.iteritems()
            }
        classImplVal = convertedValues[classInstanceDescription.classId]

        if classImplVal.isSymbol():
            convertedValues[objectId] = classImplVal
            return

        memberNames = tuple(sorted(name for name in classMemberNameToImplVal.iterkeys()))
        memberValues = tuple(classMemberNameToImplVal[name] for name in memberNames)
        convertedValueOrNone = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (classImplVal,
                 Symbol_CreateInstance,
                 ForaNative.CreateNamedTuple(memberValues, memberNames))
                )
            )

        if convertedValueOrNone is None:
            raise pyfora.PythonToForaConversionError(
                ("An internal error occurred: " +
                 "function stage 1 simulation unexpectedly returned None")
                )

        convertedValues[objectId] = convertedValueOrNone

