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

import json
import logging
import random
import re
import time
import traceback
import math
import uuid

import ufora.test.BlockingMachines as BlockingMachines
import ufora.test.Commit as Commit
import ufora.test.Branch as Branch
import ufora.test.TestResult as TestResult
import ufora.test.TestScriptDefinition as TestScriptDefinition

def pad(s, length):
    if len(s) < length:
        return s + " " * (length - len(s))
    return s[:length]


class TestDatabase(object):
    def __init__(self, kvStore):
        self.kvStore = kvStore
        self.dbPrefix = "1_"

    def getTestIdsForCommit(self, commitId):
        tests = self.kvStore.get(self.dbPrefix + "commit_tests_" + commitId)

        if tests:
            return tests
        return []

    def loadTestResultForTestId(self, testId):
        res = self.kvStore.get(self.dbPrefix + "test_" + testId)

        if not res:
            return res

        return TestResult.TestResult.fromJson(res)

    def clearAllTestsForCommitId(self, commitId):
        ids = self.getTestIdsForCommit(commitId)

        for testId in ids:
            self.kvStore.set(self.dbPrefix + "test_" + testId, None)

        self.kvStore.set(self.dbPrefix + "commit_tests_" + commitId, None)

    def updateTestListForCommit(self, commit):
        ids = sorted(commit.testsById.keys())

        self.kvStore.set(self.dbPrefix + "commit_tests_" + commit.commitId, ids)

    def updateTestResult(self, result):
        self.kvStore.set(self.dbPrefix + "test_" + result.testId, result.toJson())

    def getTestScriptDefinitionsForCommit(self, commitId):
        res = self.kvStore.get("commit_test_definitions_" + commitId)
        if res is None:
            return None

        return [TestScriptDefinition.TestScriptDefinition.fromJson(x) for x in res]

    def setTestScriptDefinitionsForCommit(self, commit, result):
        self.kvStore.set("commit_test_definitions_" + commit, [x.toJson() for x in result])

    def getTargetedTestTypesForBranch(self, branchname):
        return self.kvStore.get("branch_targeted_tests_" + branchname) or []

    def setTargetedTestTypesForBranch(self, branchname, testNames):
        return self.kvStore.set("branch_targeted_tests_" + branchname, testNames)

    def getTargetedCommitIdsForBranch(self, branchname):
        return self.kvStore.get("branch_targeted_commit_ids_" + branchname) or []

    def setTargetedCommitIdsForBranch(self, branchname, commitIds):
        return self.kvStore.set("branch_targeted_commit_ids_" + branchname, commitIds)

    def getBranchIsDeepTestBranch(self, branchname):
        result = self.kvStore.get("branch_is_deep_test_" + branchname)
        if result is None:
            if branchname == "origin/master":
                return True
            else:
                return False
        return result

    def setBranchIsDeepTestBranch(self, branchname, isDeep):
        return self.kvStore.set("branch_is_deep_test_" + branchname, isDeep)


class TestManager(object):
    VERSION = "0.0.1"

    def __init__(self, github, kvStore):
        self.github = github
        self.kvStore = kvStore
        self.testDb = TestDatabase(kvStore)

        self.mostRecentTouchByMachine = {}
        self.branches = {}
        self.commits = {}

        #dict from internalIp to properties of blocking machines
        self.blockingMachines = BlockingMachines.BlockingMachines()

    def machineRequestedTest(self, machineId):
        self.mostRecentTouchByMachine[machineId] = time.time()

    def refresh(self, lock=None):
        self.updateBranchesUnderTest(lock)

    def initialize(self):
        changes = self.updateBranchesUnderTest()
        self.loadTestResults(self.commits)

    def getCommitByCommitId(self, commitId):
        if not commitId in self.commits:
            revList = "%s ^%s^^" % (commitId, commitId)
            commitId, parentHash, commitTitle = self.github.commitIdsParentHashesAndSubjectsInRevlist(revList)[0]
            self.commits[commitId] = self.createCommit(commitId, parentHash, commitTitle)
        return self.commits[commitId]


    def getTestById(self, testId):
        #we need to add indices to this object, so that this can be fast
        for c in self.commits.values():
            for t in c.testsById:
                if t == testId:
                    return c.testsById[t]
        return None

    def clearCommitId(self, commitId):
        "Remove all test-runs associated with 'commitId'"""
        self.testDb.clearAllTestsForCommitId(commitId)

        self.commits[commitId].clearTestResults()

    def distinctBranches(self):
        return set(self.branches.keys())

    def commitsInBranch(self, branchName):
        return self.branches[branchName].commits.values()

    def getCommitToTest(self, preferCommit=None):
        """Return just the next Commit object to test (ignoring the preferred test)"""
        return self.getNextCommitAndTest(preferCommit)[0]

    def getPossibleCommitsAndTests(self, coreCount = None):
        """Return a list consisting of all possible commit/test combinations we'd consider running.

        Each item the list is a tuple

            (commit, test)

        where commit is a Commit object and 'test' is either a string giving the test name or None
        indicating that we don't know the list of commits.
        """
        result = []

        for commitId, commit in self.commits.iteritems():
            if commit.excludeFromTestingBecauseOfCommitSubject():
                pass
            elif commit.buildInProgress() or commit.isBrokenBuild():
                pass
            elif commit.needsBuild():
                testDef = commit.getTestDefinitionFor('build')
                if (testDef is not None and (coreCount is None or
                            self.blockingMachines.machineCanParticipateInTest(testDef, coreCount))):
                    result.append( (commit, 'build') )
            else:
                for testName in commit.statsByType.keys():
                    if testName != "build":
                        testDefinition = commit.getTestDefinitionFor(testName)

                        if (coreCount is None or
                                    self.blockingMachines.machineCanParticipateInTest(
                                        testDefinition,
                                        coreCount
                                        )):
                            result.append( (commit, testName) )

        return result

    def getNextCommitAndTest(self, currentCommit=None, machineId = None, internalIp = None, coreCount = None):
        t0 = time.time()
        result = self.getNextCommitAndTest_(currentCommit, machineId, internalIp, coreCount)
        logging.info("calling getNextCommitAndTest_ took %s seconds and returned %s", time.time() - t0, result)
        return result

    def getNextCommitAndTest_(self, currentCommit=None, machineId = None, internalIp = None, coreCount = None):
        commitsAndTests = self.getPossibleCommitsAndTests(coreCount)
        candidates = self.prioritizeCommitsAndTests(commitsAndTests, currentCommit)

        if not candidates:
            return None, None, None

        commit, testName = candidates[0]

        testDefinition = commit.getTestDefinitionFor(testName)

        assert testDefinition is not None, "Couldn't find %s within tests %s in commit %s. testDefs are %s" % (
            testName,
            commit.statsByType.keys(),
            commit.commitId,
            commit.testScriptDefinitions.keys()
            )

        testResult = self.blockingMachines.getTestAssignment(commit, testName, machineId, internalIp, coreCount)

        if testResult is None:
            return None, None, None

        if testResult.commitId != commit.commitId:
            commit = self.commits[testResult.commitId]

        if testResult.testId not in commit.testsById:
            commit.addTestResult(testResult,updateDB=True)
            self.testDb.updateTestResult(testResult)

        return commit, commit.getTestDefinitionFor(testResult.testName), testResult


    def heartbeat(self, testId, commitId, machineId):
        self.mostRecentTouchByMachine[machineId] = time.time()

        if commitId in self.commits:
            commit = self.commits[commitId]
            return commit.heartbeatTest(testId, machineId)
        else:
            logging.warn("Got a heartbeat for commit %s which I don't know about", commitId)
            return TestResult.TestResult.HEARTBEAT_RESPONSE_DONE

    def recordMachineResult(self, result):
        commitId = result.commitId
        testId = result.testId

        test = self.commits[commitId].testsById[testId]

        self.commits[commitId].testChanged(test.testName)

        test.recordMachineResult(result)

        self.testDb.updateTestResult(test)

        self.mostRecentTouchByMachine[result.machine] = time.time()

    def computeCommitLevels(self):
        """Given a set of Commit objects, produce a dictionary from commitId to "level",
        where 'level' is 0 for leaf commits and increases by 1 at each parent."""
        commitLevel = {}
        commitsById = {}

        commits = list(self.commits.values())

        for c in commits:
            commitsById[c.commitId] = c

        parentIds = set([c.parentId for c in commits])
        leaves = set([c for c in commits if c.commitId not in parentIds])

        def followChain(commit, level):
            if commit.commitId not in commitLevel or commitLevel[commit.commitId] > level:
                commitLevel[commit.commitId] = level

                if commit.parentId in commitsById:
                    followChain(commitsById[commit.parentId], level+1)

        for l in leaves:
            followChain(l, 0)

        return commitLevel

    def prioritizeCommitsAndTests(self, candidates, preferCommit = None):
        """
        Return a list of commit IDs sorted by priority.

        candidates - a list of (commit, testName) pairs

        The returned list is a subset of candidates ordered by preference, with most preferable
        first in the list.
        """
        # we prefer leaf commits and commits on which test progress has already
        # been made.
        commits = set([commit for (commit, testName) in candidates])

        commitLevelDict = self.computeCommitLevels()

        def scoreCommitAndTest(entry):
            return self.scoreCommitAndTest(commitLevelDict, preferCommit, entry[0], entry[1])

        sortedCommitsAndTestNames = sorted(candidates, key=scoreCommitAndTest, reverse=True)

        return sortedCommitsAndTestNames

    def scoreCommitAndTest(self, commitLevelDict, preferCommit, commit, testName):
        commitLevel = commitLevelDict[commit.commitId]

        #if this is the preferred commit, bump it up above leaves
        if commit.commitId == preferCommit:
            bump = 0.5
        else:
            bump = 0.0

        #this is a log-probability measure of how 'suspicious' this commit is
        suspiciousness = min(commit.suspiciousnessLevelForTest(testName), 10)

        #note that we use a smaller power than "e" even though it's log probability. This compresses
        #the spread of the tests so that we don't focus too much
        weightPerNonTimedOutRun = 1 / (.5 + 1.5 ** suspiciousness) / 5.0

        if testName is None:
            return 10000000000000 - commitLevel + bump
        if testName == "build":
            return 1000000000 - commitLevel + bump
        if commit.totalNonTimedOutRuns(testName) == 0:
            return 100000 - commitLevel / 10000.0 + bump
        if commit.isDeepTest or commit.isTargetedCommitAndTest(testName):
            return 1000 - commitLevel / 10000.0 - commit.totalNonTimedOutRuns(testName) * weightPerNonTimedOutRun + bump

        return 0 - commitLevel / 10000.0 - commit.totalNonTimedOutRuns(testName) / 10.0 + bump

    def getRevisionRangeForDeepTesting(self):
        res = self.kvStore.get("revisions_range_for_deep_testing")

        if res is None:
            return "origin/master ^origin/master^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"

        return res

    def updateBranchesUnderTest(self, lock=None):
        self.updateBranchList(lock)

        for branch in self.branches.values():
            branch.updateCommitsUnderTest(self, lock)

    def updateBranchList(self, lock=None):
        if lock:
            lock.release()

        branchNames = set(self.github.listBranches())

        if lock:
            lock.acquire()

        for b in branchNames:
            if b not in self.branches:
                self.branches[b] = Branch.Branch(self.testDb, b, b + " ^origin/master")

        for b in set(self.branches.keys()) - branchNames:
            del self.branches[b]

        if 'origin/master' not in self.branches:
            self.branches['origin/master'] = Branch.Branch(
                self.testDb,
                'origin/master',
                'origin/master ^origin/master' + '^' * self.masterTestDepth()
                )
        else:
            self.branches['origin/master'].updateRevList(
                'origin/master ^origin/master' + '^' * self.masterTestDepth(),
                self
                )

        self.pruneUnusedCommits()

    def pruneUnusedCommits(self):
        toPrune = set()

        for c in self.commits.values():
            if not c.branches:
                toPrune.add(c)

        for c in toPrune:
            del self.commits[c.commitId]

    def masterTestDepth(self):
        if self.kvStore.get("master_test_depth") is None:
            return 50
        return int(self.kvStore.get("master_test_depth"))

    def loadTestResults(self, commits):
        for commitId, commit in commits.iteritems():
            for testId in self.testDb.getTestIdsForCommit(commitId):
                testData = self.testDb.loadTestResultForTestId(testId)

                if testData:
                    commit.addTestResult(testData, updateDB=False)

    def createCommit(self, commitId, parentHash, commitTitle):
        if commitId not in self.commits:
            testScriptDefinitions = self.testDb.getTestScriptDefinitionsForCommit(commitId)

            if testScriptDefinitions is None:
                testScriptDefinitions = self.github.getTestScriptDefinitionsForCommit(commitId)
                self.testDb.setTestScriptDefinitionsForCommit(commitId, testScriptDefinitions)

            self.commits[commitId] = Commit.Commit(self.testDb, commitId, parentHash, commitTitle, testScriptDefinitions)

        return self.commits[commitId]


