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

class PythonToForaConversionException(Exception):
    def __init__(self, nativeError, codeDefinitionPoint):
        self.nativeError_ = nativeError
        self.codeDefinitionPoint_ = codeDefinitionPoint

    error = property(lambda self: self.nativeError_.error)
    range = property(lambda self: self.nativeError_.range)
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
        return self.error + "\n" + self.formattedRange

