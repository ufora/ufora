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

import ufora.FORA.python.ErrorFormatting as ErrorFormatting
import ufora.native.FORA as ForaNative
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import logging

class ParseException(Exception):
    def __init__(self, functionParseError, codeDefinitionPoint):
        """arguments:

        functionParseError - a FORANative.FunctionParseError
        CodeDefinitionPoint - a CodeDefinitionPoint identifying the source of the
            code that failed to parse
        """
        Exception.__init__(self)
        self.parseError_ = functionParseError
        self.codeDefinitionPoint_ = codeDefinitionPoint

    @staticmethod
    def fromMessageAndCodeLocation(message, codeLocation):
        return ParseException(
            ForaNative.FunctionParseError(
                message,
                codeLocation.range
                ),
            codeLocation.defPoint
            )

    @staticmethod
    def fromModuleParseError(parseError):
        return ParseException(
            ForaNative.FunctionParseError(
                parseError.error,
                parseError.location.range
                ),
            parseError.location.defPoint
            )

    codeLocation = property(lambda self: ForaNative.CodeLocation(self.codeDefinitionPoint_, self.parseError_.range))
    error = property(lambda self: self.parseError_.error)
    range = property(lambda self: self.parseError_.range)
    formattedRange = property(lambda self:
                    ErrorFormatting.formatCodeLocation(
                        ForaNative.CodeLocation(
                            self.codeDefinitionPoint_,
                            self.range
                            ),
                        None
                        )
                    )

    def __str__(self):
        return (self.error + "\n" + self.formattedRange)


