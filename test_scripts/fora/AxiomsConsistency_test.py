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
This class is run during the main unittest on the file axioms in ``UNIT_TEST_AXIOMS.txt''.
It can be run on any file of axiom signatures via: `python Axioms_consistency_test.py <file-name>.
To generate a full list of axioms (from which you can pick and chose),
run `python GenerateAxiomSignatures.py`. This will write to a file `ufora/FORA/Axioms/AXIOMS_TO_TEST.txt`
which is ignored by git (it's in .gitignore).
"""
import unittest
import numpy
import time
import sys
import os
import argparse
import ufora.config.Setup as Setup
import ufora.config.Mainline as Mainline
import ufora.native.CallbackScheduler as CallbackScheduler

#this program must be started from within this directory
UNIT_TEST_AXIOMS_PATH = 'AxiomsConsistency_test.txt'

import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.native.FORA as FORANative
from sets import Set
import re
import logging
import os.path

class AxiomTester(object):
    def __init__(self, numRandVals, numRelaxations, maxForRelax, maxForRand, testAxiomsPath, seed):
        object.__init__(self)
        self.callbackScheduler = CallbackScheduler.singletonForTesting()
        self.callbackSchedulerFactory = self.callbackScheduler.getFactory()
        
        self.numRandVals = numRandVals
        self.numRelaxations = numRelaxations
        self.maxForRelax = maxForRelax
        self.maxForRand = maxForRand
        self.seed = seed

        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.typed_fora_compiler = self.runtime.getTypedForaCompiler()

        if testAxiomsPath is not None:
            pathToUse = testAxiomsPath
        else:
            pathToUse = UNIT_TEST_AXIOMS_PATH

        self.axiom_signatures_to_test = self.loadAxiomSignaturesFromFile(pathToUse)

        self.axiom_groups = []
        for i in range(self.axioms.axiomCount):
            self.axiom_groups.append(self.axioms.getAxiomGroupByIndex(i))

        self.symbol_strings = self.loadSymbolStrings()

        numpy.random.seed(seed)

    def assertIsNotNone(self, thing, msg = None):
        assert thing is not None, ("Expected %s to be None" % thing if msg is None else msg)

    def assertEqual(self, lhs, rhs, msg = None):
        assert lhs == rhs, ("Expected %s and %s to be equal" % (lhs,rhs) if msg is None else msg)

    def loadAxiomSignaturesFromFile(self, axioms_file):
        """
        Loads axiom signatures from a file `axioms_file`. This file should contain
        axiom signatures on each line, but also can have commented lines (starting with a `#`)
        or commented blocks (lines surrounded by lines of `\"""`), as in python syntax.
        """
        axiom_signatures = []
        line_number = 0
        in_comment = False
        assert os.path.exists(axioms_file), (
                        "unable to open file `%s'\n"
                        %axioms_file
                        )
        with open(axioms_file) as f:
            for line in f:
                line_number += 1
                if re.search('^"""', line):
                    in_comment = (in_comment != True) # in_comment = in_comment XOR True
                    continue
                if not in_comment and not re.search('^#', line) and len(line.strip()) > 0:
                    try:
                        axiom_signatures.append(FORANative.parseStringToJOV(
                                                                line.strip()).getTuple())
                    except Exception as inst:
                        logging.warn("unable to parse to JOV: `%s', %s:%s",
                                                            line.strip(), axioms_file, line_number)
                        raise inst
        return axiom_signatures

    def loadSymbolStrings(self):
        symbol_strings_set = Set()
        symbol_strings = []
        for i in range(self.axioms.axiomCount):
            sig = str(self.axioms.getAxiomGroupByIndex(i).signature())
            for term in [l.strip(' ') for l in sig.strip("()").split(',')]:
                if re.search('^`', term):
                    if term not in symbol_strings_set:
                        symbol_strings_set.add(term)
                        symbol_strings.append(term.strip('`'))
        return symbol_strings

    def nonNumericAxiomGroups(self):
        return self.axiom_groups[:62] + self.axiom_groups[2389:]

    def vectorAxiomGroups(self):
        return [x for x in self.axiom_groups if 'ector' in str(x.signature())]

    def axiomGroupsToTest(self):
        tr = self.vectorAxiomGroups()
        tr = [x for x in tr if "::" in str(x.signature())]
        return tr


    def random_relaxation(self, jovt, max_attempts):
        relaxations = FORANative.JOVTRelaxations(jovt)
        rand_i = numpy.random.randint(len(relaxations))
        attempts = 0
        while not relaxations[rand_i].getTuple() and attempts < max_attempts:
            rand_i = numpy.random.randint(len(relaxations))
            attempts += 1
        return relaxations[rand_i].getTuple()

    def attemptToFindRandomValue(self, jovt, max_attempts_for_random_value):
        attempts = 1
        randomValue = self.randomJOVGenerator.randomValue(jovt)
        while not randomValue:
            randomValue = self.randomJOVGenerator.randomValue(jovt)
            attempts = attempts + 1
            if attempts > max_attempts_for_random_value:
                break
        return randomValue

    def evaluateNativeAxiom(self, axiom, value_as_list):
        """
        Evaluates a native axiom `axiom` on a value given as a list of
        ImplValContainers `value_as_list`
        """
        typedNativeCallTarget = axiom.getCallTarget()
        axiom_name = str(axiom.signature()) + str(time.clock())
        typedNativeFunctionPointer = self.typed_fora_compiler.compile(typedNativeCallTarget, axiom_name)
        self.context.evaluateFunctionPointer(typedNativeFunctionPointer, *value_as_list)
        finished_result = self.context.getFinishedResult()
        if finished_result.isException():
            return finished_result.asException.exception
        if finished_result.isResult():
            return finished_result.asResult.result
        raise Exception("Encountered failure!")


    def test_axiom_consistency(self):
        vdm = FORANative.VectorDataManager(
            self.callbackScheduler,
            Setup.config().maxPageSizeInBytes
            )

        self.context = ExecutionContext.ExecutionContext(dataManager = vdm)

        self.randomJOVGenerator = FORANative.RandomJOVGenerator(
            self.seed, self.context).symbolStrings(self.symbol_strings).setMaxStringLength(50)
        for jovt in self.axiom_signatures_to_test:
            axiom = self.axioms.getAxiomByJOVT(self.typed_fora_compiler, jovt)
            self.assertIsNotNone(axiom, "unable to find an axiom for the signature %s" %jovt)

            if axiom.isExpansion():
                assert False, "We can only test native expansions."
            elif axiom.isNativeCall():
                self.check_native_axiom_consistency(axiom)
            else:
                assert False, "Unexpected axiom type in signature %s" % jovt
        #os._exit(0)

    def check_class_axiom_consistency(self,
                                      axiom):
        logging.warn("axiom consistency test for class axioms has not been implemented")



    def check_native_axiom_consistency(
            self,
            axiom):

        num_rand_vals = self.numRandVals
        num_relaxations_to_try = self.numRelaxations
        max_attempts_for_random_value = self.maxForRand
        max_attempts_for_random_relax = self.maxForRelax

        jovt = axiom.signature()

        logging.info("checking native axiom with signature %s", jovt)

        least_specialized_axiom = axiom

        random_values_tried = 0
        for i in range(num_rand_vals):
            rand_val = self.attemptToFindRandomValue(jovt, max_attempts_for_random_value)
            if rand_val == None:
                continue
            value_by_least_specialized_axiom = self.evaluateNativeAxiom(least_specialized_axiom,
                                                                        rand_val.getTuple())
            random_values_tried += 1

            most_specialized_axiom = self.axioms.getAxiomByJOVT(
                                        self.typed_fora_compiler,
                                        FORANative.JOVFromLiveValue(rand_val).getTuple())
            value_by_most_specialized_axiom = self.evaluateNativeAxiom(
                                                most_specialized_axiom,
                                                rand_val.getTuple())
            self.assertEqual(value_by_least_specialized_axiom,
                             value_by_most_specialized_axiom,
                             "calling the native axioms %s and %s on %s produce different values! \
                                    (%s vs %s)"
                             %(least_specialized_axiom.signature(),
                                most_specialized_axiom.signature(),
                                rand_val,
                                value_by_least_specialized_axiom,
                                value_by_most_specialized_axiom))

            rand_val_as_jov = FORANative.implValToJOV(rand_val)
            actually_tested = 0
            for j in range(num_relaxations_to_try):
                if rand_val_as_jov.getTuple():
                    random_relaxation = self.random_relaxation(
                                            rand_val_as_jov.getTuple(),
                                            max_attempts_for_random_relax)
                    if random_relaxation and least_specialized_axiom.signature().covers(
                                                                                random_relaxation):
                        actually_tested = actually_tested + 1

                        local_best_axiom = self.axioms.getAxiomByJOVT(self.typed_fora_compiler,
                                                                        random_relaxation)
                        local_value = self.evaluateNativeAxiom(local_best_axiom,
                                                                rand_val.getTuple())
                        self.assertEqual(value_by_least_specialized_axiom,
                                         local_value,
                                         "calling the native axioms %s and %s on %s \
                                            produce different values! (%s vs %s)"
                                         %(least_specialized_axiom.signature(),
                                            local_best_axiom.signature(),
                                            rand_val,
                                            value_by_least_specialized_axiom,
                                            local_value))

        if random_values_tried == 0:
            logging.warn("unable to find a random value for the native axiom %s", jovt)

def main(parsedArguments):
    Runtime.initialize()

    tester = AxiomTester(
        parsedArguments.numRandVals,
        parsedArguments.numRelaxations,
        parsedArguments.maxForRelax,
        parsedArguments.maxForRand,
        parsedArguments.testAxiomsPath,
        parsedArguments.seed
        )

    tester.test_axiom_consistency()

def createParser():
    parser = Setup.defaultParser(
            description='Simulate an Amazon EC2 cluster'
            )

    parser.add_argument('--testAxiomsPath', default=UNIT_TEST_AXIOMS_PATH)
    parser.add_argument('--numRandVals', default=8)
    parser.add_argument('--numRelaxations', default=4)
    parser.add_argument('--maxForRelax', default=8)
    parser.add_argument('--maxForRand', default=16)
    parser.add_argument('--seed', default=0)

    return parser

if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize=[],
        parser=createParser()
        )

