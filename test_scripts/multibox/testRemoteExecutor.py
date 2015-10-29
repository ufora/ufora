import unittest
import pyfora
import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases


class TestRemoteExecutor(unittest.TestCase, ExecutorTestCases.ExecutorTestCases):
    @classmethod
    def setUpClass(cls):
        cls.executor = None

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return pyfora.connect('http://localhost:30000')

        if cls.executor is None:
            cls.executor = pyfora.connect('http://localhost:30000')
            cls.executor.stayOpenOnExit = True
        return cls.executor


if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline()
