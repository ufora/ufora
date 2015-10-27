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

"""
TestScriptDefinition

Models a single unit-test script and the resources required to execute it.
"""
class TestScriptDefinition:
    validMachineDescriptions = set(["any", "2core", "8core", "32core"])

    def __init__(self, testName, testScriptPath, machineCount):
        self.testName = testName
        self.testScriptPath = testScriptPath

        for m in machineCount:
            assert isinstance(machineCount[m], int)
            assert machineCount[m] > 0
            assert machineCount[m] < 100
            assert m in TestScriptDefinition.validMachineDescriptions

        self.machineCount = machineCount

    def toJson(self):
    	return {
    		'testName': self.testName,
    		'testScriptPath': self.testScriptPath,
    		'machineCount': self.machineCount
    		}

    @staticmethod
    def fromJson(json):
    	return TestScriptDefinition(
    		json['testName'],
    		json['testScriptPath'],
    		json['machineCount']
    		)

    def __repr__(self):
    	return "TestScriptDefinition(%s,%s,%s)" % (
    		self.testName,
    		self.testScriptPath,
    		self.machineCount
    		)

    def isSingleMachineTest(self):
        return self.totalMachinesRequired() == 1

    def totalMachinesRequired(self):
        return sum(self.machineCount.values())

    def isSatisfiedBy(self, machineCount):
        for m in self.machineCount:
            if m not in machineCount or machineCount[m] < self.machineCount[m]:
                return False
        return True

