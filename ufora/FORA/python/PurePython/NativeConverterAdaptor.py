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


import pyfora


import ufora.native.FORA as ForaNative


Symbol_CreateInstance = ForaNative.makeSymbol("CreateInstance")


class NativeConverterAdaptor(object):
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

