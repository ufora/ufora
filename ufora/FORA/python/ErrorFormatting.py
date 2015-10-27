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

"""ErrorFormatting

functions to format FORA errors
"""

import logging
import ufora.native.FORA as ForaNative

TAB_WIDTH = 4
CHOP_LENGTH = 100

def carats_(lineText, startPos, stopPos):
    """Produce spaces up to 'startPos' and '^' from startPos to stopPos. assume tabs are 4 spaces"""
    toExpandBy = lineText[startPos:stopPos].count("\t") * (TAB_WIDTH-1)
    toPrepend = lineText[:startPos].count("\t") * (TAB_WIDTH-1)
    return " " * (startPos-1 + toPrepend) + "^" * max(stopPos - startPos + toExpandBy, 1)

def errorIndicatorLine(lineText, range):
    """Produce a line indicating where in the line the range is"""
    if range.start.line == range.stop.line:
        return carats_(lineText, range.start.col, range.stop.col) + "\n"
    return ""

def formatExceptionPoint_(filename, code, textRange, lines, valuesInScope):
    """given a string of code and a SimpleParseRange, return a formatted
    exception trace"""
    if code is not None and lines:
        splitCode = code.split("\n")
        lineRange = splitCode[textRange.stop.line - 1:textRange.stop.line - 1 + lines]

        if len(lineRange) != 1:
            line = "\n\t" + "\n\t".join(lineRange)
        else:
            line = lineRange[0]
            errorIndicator = errorIndicatorLine(line, textRange)

            lineWithoutTabs = line.replace("\t", " "*TAB_WIDTH)

            line = "\n\t" + lineWithoutTabs + "\n\t" + errorIndicator

        if valuesInScope is not None and len(valuesInScope):
            line = line + "\twith\n"
            for index in range(len(valuesInScope)):
                line = line + "\t  %s: %s\n" % (
                    valuesInScope.names_[index],
                    valuesInScope[index]
                    )
            line = line + "\n"

        return "  From %s:%d%s" % (filename, textRange.stop.line, line)

    return "  From %s:%d\n" % (filename, textRange.stop.line)

def formatChop(s):
    """format a string for printing in short form"""
    if len(s) < CHOP_LENGTH:
        return s
    return s[:CHOP_LENGTH] + "..."

# dict that maps from the first element of a CodeLocation::External path
# to a function from the rest of the path sequence to a pair containing
# a label and the code itself
exceptionCodeSourceFormatters = {}

def formatCodeLocation(codeLocation, valuesInScope, lines = 1):
    defPoint = codeLocation.defPoint
    codeRange = codeLocation.range

    if defPoint.isExternal():
        elts = [x for x in defPoint.asExternal.paths]

        if elts and elts[0] in exceptionCodeSourceFormatters:
            filenameAndCode = exceptionCodeSourceFormatters[elts[0]](elts[1:])
            if filenameAndCode is not None:
                return formatExceptionPoint_(filenameAndCode[0], filenameAndCode[1], codeRange, lines, valuesInScope)
    elif defPoint.isAxioms():
        return "\tAxiom: " + str(codeRange.stop.line) + "\n"
    return ""

def formatStackTraceHash(hash, valuesInScope, lines = 1):
    codeLocation = ForaNative.getCodeLocation(hash)
    if codeLocation is not None:
        return formatCodeLocation(codeLocation, valuesInScope, lines)
    else:
        return ""

def formatStacktrace(stacktrace, valuesInScope, lines = 1):
    """given a list of CodeLocation objects, print a stacktrace

    stacktrace -- list of CodeLocation objects
    valuesInScope -- tuple?
    """
    return "".join([
        formatStackTraceHash(s, valuesInScope[index] if valuesInScope is not None else None, lines)
            for index, s in enumerate(stacktrace)])

