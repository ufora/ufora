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

"""StdinCache

Services for tracking the data passed into the REPL, including
a list of lines. Analytics for breaking the cache into pieces,
disassembling them, and matching codeblocks against them.
"""

import logging
import inspect
import traceback
import ast


singleton_ = []
def singleton():
    if not singleton_:
        singleton_.append(StdinCache())
        
    return singleton_[0]

class StdinCache:
    def __init__(self):
        self.lines = []
        self.blocks = []
        self.blockLineNumbers = []
        self.blockCodeObjects = []
        self.codeStringToCodeObjectsAndLineNumber = {}

    def refreshFromText(self, text):
        """Consume as much content as possible from the line buffer.

        Returns self, so that we can chain calls to this function and 'getlines'.
        """
        newLines = [x + "\n" for x in text.split("\n")]

        self.lines += newLines
        for block in self.divideIntoBlocks(newLines):
            self.addBlock(block)

        return self

    def refreshFromReadline(self):
        """Consume as much content as possible from the line buffer.

        Returns self, so that we can chain calls to this function and 'getlines'.
        """
        newLines = []

        #for some reason, this import segfaults if we do it as part of our routine
        #setup in the test harness. Putting the import here ensures we only
        #import it when we are actively using it (e.g. there is a terminal connected
        #to stdin)
        import readline

        while len(self.lines) + len(newLines) < readline.get_current_history_length():
            newLines.append(readline.get_history_item(len(self.lines) + len(newLines) + 1) + "\n")

        self.lines += newLines
        for block in self.divideIntoBlocks(newLines):
            self.addBlock(block)

        return self

    def divideIntoBlocks(self, lines):
        """Divide 'lines' into blocks that the interpreter would execute as a single statement."""
        blocks = []

        while lines:
            ix = self.indexOfFirstBreak(lines)

            blocks.append(lines[0:ix])
            lines = lines[ix:]

        return blocks

    def indexOfFirstBreak(self, lines):
        #chop the final newline
        startingLine = lines[0][:-1]

        blockPrefix = startingLine[:len(startingLine) - len(startingLine.lstrip())]

        def lineTerminatesBlock(index):
            if index >= len(lines):
                return True

            line = lines[index][:-1]

            if index > 0 and lines[index-1].endswith("\\\n"):
                return False

            if not line.startswith(blockPrefix):
                #this is a dedent
                return True

            if line == blockPrefix:
                #this is a new block at the same indent level
                return True

            if line[len(blockPrefix)].isspace():
                #if this line is indented
                return False

            return True

        index = 1
        while not lineTerminatesBlock(index):
            index += 1

        return index

    def getlines(self):
        return self.lines

    def addBlock(self, block):
        self.blocks.append(block)

        if not self.blockLineNumbers:
            self.blockLineNumbers.append(0)
        
        self.blockLineNumbers.append(
            self.blockLineNumbers[-1] + len(block)
            )

        code = self.codeForBlock(block)

        self.blockCodeObjects.append(code)

        self.registerCodeObject(code, self.blockLineNumbers[-2])

    def registerCodeObject(self, codeObject, codeObjectLineNumberBase):
        if codeObject.co_code not in self.codeStringToCodeObjectsAndLineNumber:
            self.codeStringToCodeObjectsAndLineNumber[codeObject.co_code] = []

        self.codeStringToCodeObjectsAndLineNumber[codeObject.co_code].append(
            (codeObject, codeObjectLineNumberBase + codeObject.co_firstlineno-1)
            )

        for child in codeObject.co_consts:
            if inspect.iscode(child):
                self.registerCodeObject(child, codeObjectLineNumberBase)

    def codeForBlock(self, block):
        try:
            return compile(ast.parse("".join(block)), "<stdin>", 'exec')
        except:
            logging.error("Failed to compile: %s", traceback.format_exc())
            return None
        
    def findCodeLineNumberWithinStdin(self, codeObject):
        if codeObject.co_code not in self.codeStringToCodeObjectsAndLineNumber:
            return None

        for child, line in self.codeStringToCodeObjectsAndLineNumber[codeObject.co_code]:
            if child.co_names == codeObject.co_names:
                return line
