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

'''
Fuzzer -- Generates Fora-esque gibberish to clobber the parser with.

TODO:
 * Sometimes leave semicolons out.
 * Check if I'm missing anything else.
'''

from numpy import random as nrandom
import random
import unittest
import logging

import ufora.native.FORA as ForaNative
import ufora.FORA.python.FORA as Fora
import ufora.FORA.python.ForaValue as ForaValue
from ufora.FORA.python.ParseException import ParseException


# sys.setrecursionlimit(5000)
emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])


class ForaLanguageParserFuzzTester(unittest.TestCase):
    '''
    A unit test which generates random
    Fora-esque gibberish and feeds it into
    the parser, and thence into the interpreter.

    The test passes if the only results from this
    process are successes or Fora exceptions;
    segfaults and failed lasserts are the things
    we're trying to weed out.
    '''

    def setUp(self):
        self._trialCount = 1000
        self._permittedAttemptCount = 10
        self._shouldPrintEveryTrial = False

    def randArity(self, minArity = 0, p = 0.4):
        return minArity + nrandom.geometric(p) - 1

    def chooseFrom(self, *options):
        return random.choice(options)()

    def repeat(self, what, sep, count):
        return sep.join(what() for _ in xrange(count))

    def severalOf(self, what, sep, minArity = 0, p = 0.4):
        return self.repeat(what, sep, self.randArity(minArity, p))

    def var(self):
        return random.choice(list('abc') + ['self'] * 10 + ['cls'] * 10)

    def tag(self):
        return '#' + self.var()

    def const(self):
        return random.choice((
            '-1',
            '0',
            '1',
            '2',
            '3,'
            '`foo',
            '`bar',
            '"bippy"',
            '"dingus"',
            '""',
            'nothing', # Repetitions like this are intentional;
            'nothing', # here, I'm increasing the probability of 'nothing'.
            'true',
            'false',
            self.tag()))

    def let(self):
        return "let " + self.severalOf(lambda: '%s = %s' % (self.pattern(), self.expr()), ', ')

    def binOp(self):
        return random.choice((
            '+',
            '-',
            '*',
            '/',
            '**',
            'and',
            'or',
            'in',
            'is',
            'is not',
            'not in'))

    def opExpr(self):
        return '%s %s %s' % (self.expr(), self.binOp(), self.expr())

    def selector(self):
        return '%s.%s' % (self.expr(), self.var())

    def subscript(self):
        return '%s[%s]' % (self.expr(), self.expr())

    def call(self):
        return self.expr() + self.tupleExpr()

    def backtickApply(self):
        return '%s`%s' % (self.expr(), self.tupleExpr())

    def tupleOf(self, elemGenerator):
        def tupleElem():
            if random.random() < 0.3:
                return '%s: %s' % (self.var(), elemGenerator())
            else:
                return elemGenerator()

        arity = self.randArity()
        return '(%s%s)' % (self.repeat(tupleElem, ', ', arity), ',' if arity is 1 else '')

    def tuplePattern(self):
        if random.random() < 0.2:
            return '(...)'
        else:
            return self.tupleOf(self.pattern)

    def tupleExpr(self):
        return self.tupleOf(self.expr)

    def vector(self):
        return '[%s]' % self.severalOf(self.expr, ', ')

    def dictionary(self):
        return '{%s}' % self.severalOf(lambda: '%s: %s' % (self.expr(), self.expr()), ', ')

    def comprehensionClause(self):
        return self.chooseFrom(
            lambda: ' for %s in %s' % (self.pattern(), self.expr()),
            lambda: ' if ' + self.expr())

    def comprehensionClauses(self):
        return 'for %s in %s%s' % (self.pattern(), self.expr(), self.severalOf(self.comprehensionClause, ''))

    def comprehension(self):
        if random.random() < 0.8:
            return '(%s%s)' % (self.expr(), self.severalOf(self.comprehensionClause, ''))
        else:
            return self.expr() + self.severalOf(self.comprehensionClause, '') # Just for kicks.

    def vectorComprehension(self):
        return '[%s]' % self.comprehension()

    def ifExpr(self):
        if random.random() < 0.4:
            return 'if (%s) %s' % (self.stmts(), self.expr())
        else:
            return 'if (%s) %s else %s' % (self.stmts(), self.expr(), self.expr())

    def whileExpr(self):
        return 'while (%s) %s' % (self.stmts(), self.expr())

    def forExpr(self):
        if random.random() < 0.9:
            return '%s %s' % (self.comprehensionClauses(), self.block())
        else:
            return '%s %s' % (self.comprehensionClauses(), self.expr()) # Grammar requires a block; test this anyway.

    def expr(self):
        return self.chooseFrom(
            self.var,
            self.var,
            self.const,
            self.const,
            self.let,
            self.let,
            self.opExpr,
            self.selector,
            self.subscript,
            self.call,
            self.backtickApply,
            self.tupleExpr,
            self.vector,
            self.dictionary,
            self.comprehension,
            self.vectorComprehension,
            self.ifExpr,
            self.whileExpr,
            self.forExpr,
            self.block,
            lambda: '(%s)' % self.stmts(),
            lambda: '(%s)' % self.expr(),
            lambda: 'break',
            lambda: 'return ' + self.expr(),
            lambda: 'yield ' + self.expr(),
            self.fun,
            self.fun,
            self.obj,
            self.cls,
            self.patternMatch,
            self.tryCatch)

    def stmts(self):
        return self.severalOf(self.expr, '; ')

    def block(self):
        return  '{ %s }' % self.stmts()

    def patternPart(self):
        return self.chooseFrom(
            self.var,
            self.var,
            self.const,
            self.tuplePattern,
            lambda: '{%s}' % self.expr(),
            lambda: '[%s]' % self.expr(),
            lambda: '*' + self.var(),
            self.tag,
            lambda: self.tag() + self.tuplePattern(),
            lambda: '%s or %s' % (self.patternPart(), self.patternPart()))

    def pattern(self):
        return self.severalOf(self.patternPart, ' ', 1, 0.8)

    def matcher(self):
        return '%s %s' % (self.tuplePattern(), self.block())

    def matchers(self):
        return self.severalOf(self.matcher, ' ', 1)

    def fun(self):
        return 'fun ' + self.matchers()

    def applyLikeObjTerm(self):
        prefix = random.choice((
            '...',
            '()',
            '[]',
            '[]='))
        return prefix + self.matchers()

    def mixinTerm(self):
        prefix = random.choice(['static ', ''])
        return prefix + 'mixin ' + self.expr()

    def objTerm(self):
        return self.chooseFrom(
            lambda: '%s: %s' % (self.var(), self.expr()),
            # lambda: 'base ' + self.expr(), # Is this still in the language?
            self.applyLikeObjTerm,
            self.mixinTerm)

    def obj(self):
        return 'object { %s }' % self.severalOf(self.objTerm, '; ')

    def dataMember(self):
        return 'member %s' % self.var()

    def constructor(self):
        return 'operator new' + self.matchers()

    def staticMethod(self):
        return 'static ' + self.objTerm()

    def classTerm(self):
        return self.chooseFrom(
            self.dataMember,
            self.constructor,
            self.staticMethod,
            self.objTerm)

    def cls(self):
        tr = 'class { %s }' % self.severalOf(self.classTerm, '; ')

        print tr

        return tr

    def patternMatch(self):
        return 'match %s with %s' % (self.tupleExpr(), self.matchers())

    def tryCatch(self):
        return 'try %s catch %s' % (self.block(), self.matchers())

    def testFuzzForaParser(self):
        funcParseErrorCount = 0
        foraExceptionCount  = 0
        parseSuccessCount   = 0
        fuzzAbortCount      = 0

        self._didCrash = True

        try:
            for i in xrange(self._trialCount):
                self._indexOfLastTrialRun = i

                s = ''

                try:
                    for _ in xrange(self._permittedAttemptCount):
                        try:
                            # We wrap the expression in a member selection
                            # so that the code is never actually evaluated.
                            # (The definition of `var` ensures 'm' is never
                            # actually a member of the result of the expr.)
                            # This is important, in case the expression is,
                            # say, 'while (true) nothing'.
                            s = 'fun(){%s}.m' % self.cls()
                        except KeyboardInterrupt as e:
                            raise e
                        except RuntimeError: # Stack overflow.
                            continue
                        else:
                            break
                    else:
                        fuzzAbortCount += 1
                        continue

                    self._lastTriedString = s

                    if self._shouldPrintEveryTrial:
                        logging.info('\t' + s)

                    result = Fora.eval(s)
                    if isinstance(result, ForaNative.FunctionParseError):
                        funcParseErrorCount += 1
                    else:
                        parseSuccessCount += 1
                except ParseException:
                    funcParseErrorCount += 1
                except ForaValue.FORAException:
                    foraExceptionCount += 1

            self._didCrash = False

        finally:
            logging.info('Results: %d success%s, %d parse error%s, %d fora exception%s, %d aborted fuzz%s; %d, in total.' % (
                parseSuccessCount,
                '' if parseSuccessCount   == 1 else 'es',
                funcParseErrorCount,
                '' if funcParseErrorCount == 1 else 's',
                foraExceptionCount,
                '' if foraExceptionCount  == 1 else 's',
                fuzzAbortCount,
                '' if foraExceptionCount  == 1 else 'es',
                parseSuccessCount + funcParseErrorCount + foraExceptionCount + fuzzAbortCount))

    def tearDown(self):
        if self._didCrash:
            msg = '\tCrashed, on trial %d; generated input was:\n\t%s' % (self._indexOfLastTrialRun, self._lastTriedString)
            logging.error(msg)
        else:
            msg = '\tNo crash detected. Last trial was #%d, with input: \n\t%s' % (self._indexOfLastTrialRun, self._lastTriedString)
            logging.info(msg)

