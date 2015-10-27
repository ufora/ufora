#!/usr/bin/env python

# encoding: utf-8

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
fora

primary command-line interface to FORA
"""

import ufora.config.Setup as Setup

import sys

#Windows boxes need 'pyreadline' rather than 'readline'
if sys.platform == "linux2" or sys.platform == "darwin":
    import readline
else:
    import pyreadline as readline

import time
import ufora.FORA.python.FORA as FORA


import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.FORA.python.ParseException as ParseException
import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.config.Mainline as Mainline
import ufora.FORA.python.Exceptions as Exceptions
import ufora.FORA.python.ErrorFormatting as ErrorFormatting
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.native.CallbackScheduler as CallbackScheduler
import argparse

evalHistory = []
def evalExceptionNameAndCode(hist):
    try:
        return "Eval expression " + hist[0], evalHistory[int(hist[0])]
    except:
        return None

ErrorFormatting.exceptionCodeSourceFormatters["EvalLoop"] = evalExceptionNameAndCode

class UnbalancedException(Exception):
    def __init__(self, delimiter, pos):
        self.delimiter = delimiter
        self.pos = pos
    def __str__(self):
        fmt = "unexpected {0} encountered at position {1}"
        return fmt.format(self.delimiter, self.pos)

def balance_pos(str, pos=0, close_delim=None):
    """Return the first position past an instance of `close_delim` in
    `str[pos:]` at which all pairing characters are balanced.

    "Pairing characters" include braces, square brackets, parentheses, and
    quotes (single and double, alone or as triple-quotes).

    If the end of the string is reached before all nested pairing characters
    are fully balanced (and `str` is thus a prefix of a balanced string), then
    `len(str) + 1` is returned. If the string's nesting is fundamentally broken
    and cannot be balanced with additional characters, then an
    `UnbalancedException` is raised.

    Setting `pos` starts the parse from a different position in the input
    string, and `close_delim` stops parsing when the given character is
    encountered (instead of end-of-string). Both are provided primarily to
    allow the call to be used recursively.

    Ideally this test would be pushed to the actual FORA parser, but that has
    turned out to be a more involved project than would be ideal.
    """
    # Note that this implementation is relatively slow (scanning ahead for
    # special characters with a regex may be faster), but should be sufficient
    # for interactive text entry.
    if close_delim in ("'", '"', "'''", '"""'):
        # Quotes strings aren't recursive, but allow backslash escapes:
        while pos < len(str):
            if str.startswith(close_delim, pos):
                return pos + len(close_delim)
            if str[pos] == '\\':
                pos += 1
            pos += 1
        return pos
    while pos < len(str):
        assert close_delim is None or len(close_delim) == 1
        if str[pos] == close_delim:
            return pos + 1
        elif str[pos] in ')}]':
            raise UnbalancedException(str[pos], pos)
        if str[pos] == '(':
            pos = balance_pos(str, pos + 1, ')')
        elif str[pos] == '[':
            pos = balance_pos(str, pos + 1, ']')
        elif str[pos] == '{':
            pos = balance_pos(str, pos + 1, '}')
        elif str[pos] == "'":
            if str.startswith("'''", pos):
                pos = balance_pos(str, pos + 3, "'''")
            else:
                pos = balance_pos(str, pos + 1, "'")
        elif str[pos] == '"':
            if str.startswith('"""', pos):
                pos = balance_pos(str, pos + 3, '"""')
            else:
                pos = balance_pos(str, pos + 1, '"')
        else:
            pos += 1
    return pos if close_delim is None else pos + 1

def test_balance():
    well_balanced = [ 'foo bar baz', '(1 + 2, 3)', '(((()()()(()))()))',
                      '[{([[{{(("\\""))}}]])}]' ]
    partial = [ '{()' ]
    unbalanced = [ '(}' ]
    for expr in well_balanced:
        assert balance_pos(expr) == len(expr)
    for expr in partial:
        assert balance_pos(expr) == len(expr) + 1
    for expr in unbalanced:
        assert balance_pos(expr) == -1

def interactive_expressions():
    try:
        index = 1
        while True:
            try:
                code = raw_input('%d fora-> ' % index)

                while balance_pos(code) != len(code):
                    code += "\n" + raw_input('%d -----> ' % index)

                yield (code, index)
                index = index + 1
            except UnbalancedException, e:
                print "Error: unbalanced delimiter."
            except KeyboardInterrupt:
                #not an error - just a reset indication
                index = index + 1
                print "\n\n\t[Interrupted]\n"

    except EOFError:
        # Not an error; just the end of input.
        print # make sure following output starts on a new line
        return

#TODO BUG brax: fora command-line should leave objects as FORA objects in the repl environment
#
#Otherwise, we get python objects mixed in, which is weird. This is different
#than what we want to happen when we're accessing FORA from python itself.

def handleEvalForaException(exception):
    try:
        print "\n\t" + str(exception).replace("\n", "\n\t") + "\n"
    except ForaValue.FORAException as e:
        print ("\n\tfailed to convert result to a string:\n" +
            str(e).replace("\n", "\n\t") + "\n")

def handleFailure(failure):
    print "Failure:\n\n" + failure.toString()

def handleEvalImportException(exception):
    print "ImportError:\n\n" + str(exception)

def handleEvalParseException(exception):
    print "ParseError:\n\n" + str(exception)

def handleClusterException(exception):
    print "ClusterError:\n\n" + str(exception) + '\n'

def handleEvalResult(result):
    if result is not None:
        try:
            print "\n\t" + str(result).replace("\n", "\n\t") + "\n"
        except ForaValue.FORAException as e:
            print ("\n\tfailed to convert result to a string:\n" +
                str(e).replace("\n", "\n\t") + "\n")

def eval_expression(code, locals, showTimes=False, index = None):
    evaluateStartTime = time.time()
    try:
        evalHistory.append(code)

        result = FORA.eval(
            code,
            locals,
            parsePath = ["EvalLoop", str(len(evalHistory) - 1)]
            )

        locals["result"] = result
        handleEvalResult(result)

    except ModuleImporter.FORAImportException as e:
        handleEvalImportException(e)
    except ParseException.ParseException as e:
        handleEvalParseException(e)
    except ForaValue.FORAFailure as e:
        handleFailure(e.error)
    except ForaValue.FORAException as e:
        handleEvalForaException(e)
    except Exceptions.ClusterException as e:
        handleClusterException(e)


    evaluateFinishTime = time.time()

    if showTimes:
        print "[eval time {0}]".format(
            evaluateFinishTime - evaluateStartTime
        )

usage_string = '''fora [-e 'expr'] [options] file1 file2 ...'''

epilog = '''
evaluates 'expr' and any commands from files on the command line. if no
expressions or files are given, pulls commands interactively and executes them.

fora checks the environment FORAPATH to find paths where FORA modules reside.
FORA modules consist of a file ending in .fora and a directory (of the same
name without the 'fora' extension) containing submodules (structured the same
way).

in interactive mode, 'result' is always the last expression.

Ctrl-d to exit.

'''


def createParser():
    parser = Setup.defaultParser(
            minimalParser=True,
            description = "command line interpreter for FORA",
            epilog = epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter
            )
    parser.add_argument(
        '-i',
        '--interpreter',
        dest='alwaysRunInterpreted',
        action='store_true',
        default=False,
        required=False,
        help="always run interactively"
        )
    parser.add_argument(
        '-t',
        '--time',
        dest='shouldPrintEvaluationTime',
        action='store_true',
        default=False,
        required=False,
        help="show timestamps between runs"
        )
    parser.add_argument(
        '-e',
        '--expression',
        dest='expressionsToEvaluate',
        action='append',
        required=False,
        default = [],
        help="add an expression to the evaluate list"
        )
    parser.add_argument(
        '-r',
        '--repeat_expression',
        dest='repeaters',
        action='append',
        required=False,
        default = [],
        help="add an expression to be evaluated repeatedly"
        )

    parser.add_argument(
        'files',
        nargs='*',
        help='names of files to be evaluated'
        )

    return parser


def createViewFactory():
    callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
    return ViewFactory.ViewFactory.TcpViewFactory(
        callbackSchedulerFactory.createScheduler('fora-interpreter', 1),
        'localhost',
        Setup.config().sharedStatePort
        )


def main(parsedArguments):
    isLocalEvaluator = True
    with createViewFactory():
        FORA.initialize(useLocalEvaluator=isLocalEvaluator)

    locals = {}
    try:
        for code in parsedArguments.expressionsToEvaluate:
            eval_expression(code, locals, parsedArguments.shouldPrintEvaluationTime)

        for a in parsedArguments.files:
            with open(a) as f:
                code = f.read()
            eval_expression(code, locals, parsedArguments.shouldPrintEvaluationTime)

        if parsedArguments.repeaters:
            while True:
                for r in parsedArguments.repeaters:
                    eval_expression(r, locals, parsedArguments.shouldPrintEvaluationTime)

                Evaluator.evaluator().flush()

        if parsedArguments.alwaysRunInterpreted or (
                not parsedArguments.expressionsToEvaluate and
                not parsedArguments.files and
                not parsedArguments.repeaters
                ):
            for code, index in interactive_expressions():
                try:
                    eval_expression(code, locals, parsedArguments.shouldPrintEvaluationTime, index)
                except KeyboardInterrupt:
                    print "\n\n\t[Interrupted]\n"


    except KeyboardInterrupt:
        print "\n\n\t[Interrupted]\n"

    except Exceptions.FatalException as ex:
        print "\nERROR: " + ex.message
        print "Exiting FORA."
        import os
        os._exit(os.EX_UNAVAILABLE)


    time.sleep(.5)


if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize = [],
        parser = createParser()
        )


