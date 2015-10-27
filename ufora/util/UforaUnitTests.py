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

import urllib
import unittest
import re
import time
import json
import requests




def responseAsJson(res):
    return json.loads(res.content)

def emailToUserId(email):
    userId = re.sub(r'\W', '', email)
    userId = re.sub(r'^\d+', '', userId)
    return userId

class UforaUnitTests(unittest.TestCase):
    @classmethod
    def login(cls, hostname, email, password, port=443, machineType=('medium',8)):
        cls.client = None
        cls.hostname = hostname

        cls.email = email
        cls.username = emailToUserId(email)

        cls.password = password
        cls.port = port
        cls.machineType = machineType

        cls.version = '2013-08-23'
        cls.baseUrl = "https://%s:%s/api/%s" % (cls.hostname, cls.port, cls.version)


        try:
            client = requests.session()
            r = client.post(
                    "https://%s:%s/login" % (cls.hostname , cls.port),
                    data={'username': cls.email, 'password': cls.password},
                    verify=False,
                    allow_redirects=False
                    )

            assert 'x_ufora_login_success' in r.headers and r.headers['x_ufora_login_success'] == \
                'true', "invalid login credentials"

            cls.client = client
        except:
            raise

    @classmethod
    def logout(cls):
        cls.client = None

    @classmethod
    def get(cls, url, *args, **kwargs):
        cls.assertLoggedIn()
        return cls.client.get(cls.baseUrl + url, *args, **kwargs)

    @classmethod
    def post(cls, url, *args, **kwargs):
        cls.assertLoggedIn()
        assert cls.client is not None, "User must call login before running tests"
        return cls.client.post(cls.baseUrl + url, *args, **kwargs)


    @classmethod
    def assertLoggedIn(cls):
        assert hasattr(cls, 'client'), "No login detected"
        assert cls.client is not None, "No login detected"

    @classmethod
    def getCoreCount(cls):
        cls.assertLoggedIn()
        clusterUrl = "/cluster/users/%s" % cls.username
        active = responseAsJson(cls.get(clusterUrl))['active']
        return active.get(cls.machineType[0], 0) * cls.machineType[1]


    @classmethod
    def setCoreCount(cls, count):
        cls.assertLoggedIn()
        assert count % cls.machineType[1] == 0, "core count must be a mutiple of %s" % cls.machineType[1]
        data = json.dumps({cls.machineType[0]: count / cls.machineType[1]})

        clusterUrl = "/cluster/users/%s" % cls.username

        headers = {
            'Content-Type' : 'application/json',
            'Accept' : 'text/html'
            }

        cls.post(clusterUrl, data=data, headers=headers).content

        activeCount = cls.getCoreCount()
        while activeCount != count:
            activeCount = cls.getCoreCount()
            time.sleep(1)


    def getChildrenOfKind(self, project, kind, matchingRegex=None):
        res  = self.get("/users/%s/projects/%s" % (self.username, project))
        self.assertNotEqual(responseAsJson(res).get('status'), 'badPath', 'project %s does not exist' % project)
        tr = {}
        for child in responseAsJson(res)['children']:
            child = child[1]
            if matchingRegex is None or re.match(matchingRegex, child):
                childResponse = self.get("/users/%s/projects/%s/%s" % (self.username, project, child))
                if responseAsJson(childResponse)['kind'] == kind:
                    tr[child] = childResponse
        return tr

    def assertNotTimedOut(self, response, arguments):
        self.assertNotEqual(
            responseAsJson(response).get('status'),
            'timedOut',
            "%(scope)s timed out" % arguments
        )

    def computeArguments(self, arguments, timeout):
        r = self.get("/compute/evaluate?" + urllib.urlencode(arguments), timeout=timeout+10)
        self.assertNotTimedOut(r, arguments)
        return r

    def verifyScripts(self, project, timeout=3600, matchingRegex=None):
        self.assertLoggedIn()

        passedAllTests = True
        failedString = ""

        for child, childResponse in self.getChildrenOfKind(project, 'script', matchingRegex=matchingRegex).items():
            arguments = {
                'expression' : child + ";0;",
                'scope' : '.'.join(['users', self.username, 'projects', project]),
                'format' : 'json',
                'timeout' : timeout
                }
            res = self.computeArguments(arguments, timeout)
            response = responseAsJson(res)
            if response.get('status') == 'exception':
                failedString += "%s.%s\n  %s\n" % (arguments['scope'], child, response['message'])
                passedAllTests = False

        self.assertTrue(passedAllTests, 'Some tests failed:\n\n' + failedString)


    def verifyModules(self, project, timeout=3600, matchingRegex=None):
        self.assertLoggedIn()

        passedAllTests = True
        failedString = ""
        resultsString = ""

        for child, childResponse in self.getChildrenOfKind(project, 'module').items():
            testArgs = child
            if matchingRegex is not None:
                testArgs += ', "%s"' % matchingRegex.replace('\\', '\\\\')

            expression = ""\
                "runTests(%s).apply(fun(result) {"\
                "    if (result.isPass)"\
                "        return (String(result.name), (true, ''))"\
                "    return (String(result.name), (false, String(result.value)))"\
                "    })" % testArgs

            arguments = {
                'expression' : expression,
                'scope' : '.'.join(['users', self.username, 'projects', project]),
                'format' : 'json',
                'timeout' : timeout
                }

            r = self.computeArguments(arguments, timeout)

            for testName, (testResult, exceptionText) in responseAsJson(r)['result']:
                testName = testName.replace('`', '')
                if not testResult:
                    passedAllTests = False
                    failedString += "%s.%s.%s\n  %s\n" % (arguments['scope'], child, testName, exceptionText)
                resultsString += "%s.%s.%s %s\n" % (arguments['scope'], child, testName, 'failed' if not testResult else 'passed')


        self.assertTrue(passedAllTests, 'Some tests failed:\n\n' + failedString)

    def verifyProject(self, project, timeout=3600, matchingRegex=None):
        self.verifyScripts(project, timeout=timeout, matchingRegex=matchingRegex)
        self.verifyModules(project, timeout=timeout, matchingRegex=matchingRegex)


class SampleUnitTest(UforaUnitTests):
    '''
    This class is an example of how to write a unit test using ufora.

    'setUpClass' performs some global initialization such as logging in
    and adding cores to use for computation. The parameters to cls.login
    are placeholder values and should be replaced with the appropriate
    values for a given target.

    The argument for 'verifyModules' is the project that the user desires
    to run tests on.

    An example can be found in Demo projects named TutorialExamples. The
    module unitTestExamples contains the tests. In order for the snippet
    below to work, the TutorialExamples project must be duplicated to the
    users's private projects.

    Similarly, verifyScripts checks that each script in a project does
    not throw an exception when run.

    Finally, verifyProject runs both verifyScripts and verifyModules.

    '''
    @classmethod
    def setUpClass(cls):
        cls.login('demo.ufora.com', '<username>', '<password>', machineType=('large', 30))
        cls.startCoreCount = cls.getCoreCount()
        cls.setCoreCount(30)

    @classmethod
    def tearDownClass(cls):
        cls.setCoreCount(cls.startCoreCount)

    def test_modules(self):
        self.verifyModules('TutorialExamples_dup')

    def test_script(self):
        self.verifyScripts('TutorialExamples_dup')




if __name__ == "__main__":
    unittest.main()


