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

import os
import unittest
import ufora.config.Setup as Setup
import ufora.core.SubprocessRunner as SubprocessRunner
import ufora.test.ClusterSimulation as ClusterSimulation


class PyforaInJupyterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Setup.config()
        cls.executor = None
        cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulation.startService()
        cls.simulation.getDesirePublisher().desireNumberOfWorkers(1)

        cls.cur_dir = os.path.dirname(os.path.realpath('__file__'))

    @classmethod
    def tearDownClass(cls):
        cls.simulation.stopService()

    def evaluateNotebookInSubprocess(self, notebookPath):
        return SubprocessRunner.callAndReturnResultAndOutput(
            ['jupyter', 'nbconvert', '--stdout', 
             '--ExecutePreprocessor.enabled=True', notebookPath]
            )

    def assertNotebookThrowsNoExceptions(self, notebookPath):
        returnCode, output, err = \
            self.evaluateNotebookInSubprocess(notebookPath)

        self.assertEqual(returnCode, 0, msg=(returnCode, output, err))

    def test_notebooksThrowNoExceptions(self):
        notebooks_dir = os.path.join(self.cur_dir, "notebooks")

        for dirpath, _, file_names in os.walk(notebooks_dir):
            for file_name in file_names:
                if file_name.endswith(".ipynb"):
                    self.assertNotebookThrowsNoExceptions(
                        os.path.join(dirpath, file_name)
                        )

    def test_notebooks_which_throw_exceptions_fail_html_conversion(self):
        notebook_which_throws_exception_path = \
            os.path.join(self.cur_dir, "throws_exception.ipynb")

        returnCode, output, err = self.evaluateNotebookInSubprocess(
            notebook_which_throws_exception_path)

        errString = "\n".join(err)

        self.assertEqual(returnCode, 1)
        self.assertEqual(output, [])
        self.assertIn("ERROR | Error while converting", errString)
        self.assertIn(
            "CellExecutionError: An error occurred while executing the following cell",
            errString
            )
        self.assertIn("ZeroDivisionError", errString)

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline()

