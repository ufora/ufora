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


class RegularPythonContext:
    def __init__(self, memoryLimitBytes = None):
        if memoryLimitBytes is not None:
            assert isinstance(memoryLimitBytes, int)

        self._memoryLimitBytes = memoryLimitBytes

    def memoryLimitBytes(self, bytecount):
        return RegularPythonContext(int(bytecount))

    def memoryLimitMB(self, mb):
        return self.memoryLimitBytes(1024 * 1024 * mb)

    def __enter__(self):
        pass

    def __exit__(self, excType, excValue, trace):
        pass

    def __pyfora_context_apply__(self, body):
        res =  __inline_fora(
            """fun(@unnamed_args:(body, bytes), ...) {
                    try {
                        let args = (body,)
                        
                        if (bytes is not PyNone(nothing))
                            args = args + (#MemoryLimitBytes(bytes.@m),)

                        cached`(#OutOfProcessPythonCall(*args));
                        }
                    catch (e)
                        {
                        throw InvalidPyforaOperation("An unknown error occurred processing code out-of-process: " + String(e))
                        }
                }"""
                )(body, self._memoryLimitBytes)

        return res

python = RegularPythonContext()
