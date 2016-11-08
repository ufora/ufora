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
