class RegularPythonContext:
    def __enter__(self):
        pass

    def __exit__(self, excType, excValue, trace):
        pass

    def __pyfora_context_apply__(self, body):
        res =  __inline_fora(
            """fun(@unnamed_args:(body), ...) {
                    try {
                        cached`(#OutOfProcessPythonCall(body));
                        }
                    catch (e)
                        {
                        throw InvalidPyforaOperation("An unknown error occurred processing code out-of-process.")
                        }
                }"""
                )(body)

        return res

python = RegularPythonContext()