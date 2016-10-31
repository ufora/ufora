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
import logging
import ufora.core.SubprocessRunner as SubprocessRunner
import ufora.config.Setup as Setup
import ufora.test.ClusterSimulation as ClusterSimulation


class TestSubscribableWebObjectsOverSocketIO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Setup.config()
        cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulation.startService()

    @classmethod
    def tearDownClass(cls):
        cls.simulation.stopService()


    def testUsingCoffeescript(self):
        args = ["mocha",
                "--reporter", "spec",
                "--compilers", "coffee:coffee-script/register",
                "testSubscribableWebObjects.coffee",
                "-b"]

        def onOut(l):
            logging.info("Mocha Out> %s", l)
        def onErr(l):
            logging.info("Mocha Err> %s", l)

        subprocess = SubprocessRunner.SubprocessRunner(args, onOut, onErr)
        subprocess.start()
        result = subprocess.wait(720)
        subprocess.stop()

        self.assertEqual(result, 0)

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

