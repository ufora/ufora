from ufora.FORA.python.PurePython.testModules.same_line_number.B import B


class A(object):
    def __init__(self, m):
        self.m = m

    def foo(self):
        return B(self.m)
