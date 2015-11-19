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

import unittest
import pyfora
import sys
import textwrap
import time
import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases
import ufora.config.Setup as Setup
import pexpect
import ufora.test.ClusterSimulation as ClusterSimulation

class CommandlineSimulationTest(unittest.TestCase):
    """Executes 'commandline' tests against python. 

    We run python code, and verify we don't see 'Traceback' in the output.

    Note that this is a finicky test mechanism - checking for a string is not ideal.
    But because we want to check python's behavior when it's connected to a TTY,
    we need to do this at the text level (as if we had ssh'd to the python process).
    """
    @classmethod
    def setUpClass(cls):
        cls.config = Setup.config()
        cls.executor = None
        cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulation.startService()
        cls.simulation.getDesirePublisher().desireNumberOfWorkers(1)

        cls.waitUntilConnected()

    @classmethod
    def tearDownClass(cls):
        cls.simulation.stopService()

    @classmethod
    def waitUntilConnected(cls, timeout = 30.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            res = cls.execTest("import pyfora\nconnection = pyfora.connect('http://localhost:30000')\nassert connection is not None\n", 10.0)
            if res == 0:
                return
            else:
                print "Failed to connect to the simulation. Trying again."

        raise UserWarning("Failed to connect to the simulation.")

    @classmethod
    def execTest(cls, content, timeout, disableOutput=True):
        """Pass 'content' through a python interpreter and check that the output has no 'Traceback'

        timeout - max time to wait for completion.
        disableOutput - set to False to dump output to the screen during test.

        returns 1 on Failure, 0 on success (like a process error code).
        """
        child = pexpect.spawn(sys.executable + " -i")
        if disableOutput:
            child.logfile=None
        child.send(content + "\nexit(0)\n")

        out = []
        t0 = time.time()
        hitEOF = False
        while not hitEOF and time.time() - t0 < timeout:
            res = ""
            try:
                res = child.read_nonblocking(10000)
            except pexpect.EOF:
                hitEOF = True

            if not disableOutput:
                sys.stdout.write(res)
                sys.stdout.flush()

            out.append(res)
            time.sleep(0.01)

        out = "".join(out)

        if child.isalive():
            try:
                child.terminate()
                return 1
            except:
                pass

        if "Traceback" in out:
            return 1
        return 0

    def testHarnessExceptionsFail(self):
        self.assertEqual(
            self.execTest(
                textwrap.dedent("""
                    assert 10 == 11
                    """), 
                60.0
                ),
            1
            )


    def testCanConnect(self):
        self.assertEqual(
            self.execTest(
                textwrap.dedent("""
                    import pyfora
                    ufora = pyfora.connect('http://localhost:30000')

                    with ufora.remotely.downloadAll():
                        x = 10

                    assert x == 10
                    """), 
                60.0
                ),
            0)


    def testCanConnect(self):
        self.assertEqual(
            self.execTest(
                textwrap.dedent("""
                    import pyfora
                    ufora = pyfora.connect('http://localhost:30000')

                    with ufora.remotely.downloadAll():
                        x = 10

                    assert x == 10
                    """), 
                60.0
                ),
            0)


    def testCanAccessClosures(self):
        self.assertEqual(
            self.execTest(
                textwrap.dedent("""
                    import pyfora
                    ufora = pyfora.connect('http://localhost:30000')

                    def f(x):
                        return x + 1000

                    def gMaker(x):
                        def g(y):
                            return y+x
                        return g

                    g = gMaker(10)

                    with ufora.remotely.downloadAll():
                        x = f(100) + g(1)

                    assert x == 1111, x
                    """), 
                60.0
                ),
            0)

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline()

