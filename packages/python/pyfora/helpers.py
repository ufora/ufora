class RegularPythonContext:
    def __enter__(self):
        pass

    def __exit__(self, excType, excValue, trace):
        pass

    def __pyfora_context_apply__(self, body):
        res =  __inline_fora(
            """fun(@unnamed_args:(body), ...) {
                       cached`(#ExternalIoTask(#OutOfProcessPythonCall(body)));
                       }"""
                )(body)

        return res

python = RegularPythonContext()