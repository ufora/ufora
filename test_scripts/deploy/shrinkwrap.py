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

import tempfile
import unittest
import os
import shutil
import sys
import re
import ufora.core.SubprocessRunner as SubprocessRunner

rootPythonPath = os.path.split(os.path.split(os.path.abspath(os.path.split(__file__)[0]))[0])[0]
shrinkwrapScriptPath = os.path.join(rootPythonPath, "ufora", "scripts", "shrinkwrap.py")

class ShrinkwrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shrinkwrapPath = tempfile.mkdtemp()

        result, stdOut, stdErr = SubprocessRunner.callAndReturnResultAndOutput(
            ["ufora/scripts/shrinkwrap.py", "--source", rootPythonPath, 
             "--dest", cls.shrinkwrapPath],
            timeout = 240.0,
            env=None
            )

        assert result == 0, (result, stdOut, stdErr)

    def validDockerTags(self):
        return [
            "ubuntu:14.04",
            "ubuntu:12.04",
            "centos:6.6"
            ]

    def executeInDocker(self, dockerTag, args):
        standardPath = "/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/sbin:/bin"

        shrinkwrappedPathVariable = ":".join([os.path.abspath(self.shrinkwrapPath + "/dependencies/" + p) for p in standardPath.split(":")])

        return SubprocessRunner.callAndReturnResultAndOutput(
            ["docker","run"] + 
                ["-e","PATH=" + shrinkwrappedPathVariable + ":" + standardPath] +
                #so that we get 'ufora'
                ["-e","PYTHONPATH=" + self.shrinkwrapPath] +
                ["-w",self.shrinkwrapPath] +
                ["-v",self.shrinkwrapPath + ":" + self.shrinkwrapPath] + 
                [dockerTag] + 
                args    
            )

    def test_pythonExists(self):
        self.assertTrue(os.path.exists(os.path.join(self.shrinkwrapPath, "dependencies", "usr", "bin", "python")))

    def test_nodeJsRuns(self):
        for tag in self.validDockerTags():
            self.assertDockerOutput(
                tag, 
                ["node", "-e", "1+2", "--print"],
                "3"
                )

    def test_isRelocatable(self):
        for tag in self.validDockerTags():
            newDir = tempfile.mkdtemp()

            for item in os.listdir(self.shrinkwrapPath):
                shutil.move(
                    os.path.join(self.shrinkwrapPath, item),
                    os.path.join(newDir, item)
                    )

            ShrinkwrapTest.shrinkwrapPath = newDir

            result, output, err = self.executeInDocker(tag, ["bash","updateAbsolutePaths.sh"])

            self.assertEqual(
                result, 0,
                self.failureMessage(tag,result,output,err)
                )

        self.assertTrue(newDir == self.shrinkwrapPath)

        self.test_foreverRuns()
        self.test_coffeeRuns()
        self.test_pythonExists()
        self.test_pythonRuns()
        self.test_pythonCanExecuteForaCode()

    def test_foreverRuns(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["forever", "list"])

            self.assertEqual(
                result, 0,
                self.failureMessage(tag,result,output,err)
                )

            self.assertTrue('No forever processes' in output[0])

    def test_coffeeRuns(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["coffee", "-v"])

            self.assertTrue(result == 0)
            self.assertTrue('CoffeeScript' in output[0])

    def test_redisRuns(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["redis-cli", "-v"])

            self.assertTrue(result == 0)
            self.assertTrue('redis' in output[0])

    def test_pythonRuns(self):
        for tag in self.validDockerTags():
            self.assertDockerOutput(
                tag, 
                ["python", "-c", "import sys\nprint sys.version"],
                sys.version.split("\n")
                )

    def test_pythonImportPathIsCorrect(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["python", "-c", "import shutil\nprint shutil.__file__"])

            self.assertEqual(
                output, [os.path.join(self.shrinkwrapPath, "dependencies", "usr", "lib", "python2.7","shutil.pyc")], 
                self.failureMessage(tag,result,output,err)
                )

    def test_pythonCanExecuteForaCode(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["python", "ufora/FORA/python/fora_interpreter.py", "-e", "1+2"])
            output = output[-2].strip()
            self.assertEqual(
                output, "3", 
                self.failureMessage(tag,result,output,err)
                )

    def test_canExecuteMainPythonUnitTestFramework(self):
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["python", "test.py", "-py", "-filter=json"])

            pat = r'Ran ([0-9]+) tests'
            lines = [re.match(pat, x) for x in output + err]
            lines = [x for x in lines if x is not None]

            assert len(lines) == 1
            assert int(lines[0].groups()[0]) > 0

    def test_canResolveLocalhost(self):
        #if glibc is messed up, then the socket functions won't work
        for tag in self.validDockerTags():
            result, output, err = self.executeInDocker(tag, ["python", "-c", "import socket; print socket.gethostbyname('localhost')"])
            self.assertEqual(
                output, ["127.0.0.1"],
                self.failureMessage(tag,result,output,err)
                )

    def assertDockerOutput(self, tag, dockerCmd, expected):
        result, output, err = self.executeInDocker(tag, dockerCmd)

        output = [x.strip() for x in output]
        expected = [x.strip() for x in expected]

        self.assertEqual(output, expected, "Running %s\nExpected %s\nGot %s." % (dockerCmd, expected, output) + self.failureMessage(tag, result, output, err))


    def failureMessage(self, tag, result, output, err):
        return (
            "Failed for tag %s:\nResult code: %s\nOutput:\n%s\nErr:\n%s\n" % 
                (tag, result, "\n".join(output), "\n".join(err))
            )


    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.shrinkwrapPath)



if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])


