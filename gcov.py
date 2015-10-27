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

import os
import subprocess
import fnmatch
import time


import waflib.Context as Context

def options(opt):
    opt.add_option(
            '--coverage',
            action = 'store_true',
            dest = 'with_gcov',
            help = 'Use gcov for code coverage measurement',
            default = False)

def configure(conf):
    if conf.options.with_gcov:
        conf.env.isCoverageBuild = True
        conf.start_msg('Checking for `gcov` (code coverage tool)')
        conf.find_program('gcov', var='GCOV')
        conf.end_msg(conf.env.get_flat('GCOV'))

        gcov_flags = ['-fprofile-arcs', '-ftest-coverage']
        conf.env.append_unique('CXXFLAGS', gcov_flags)
        conf.env.append_unique('LINKFLAGS', gcov_flags)

        conf.env.append_unique('CXXDEFINES', 'COVERAGE_BUILD')

def analyze(ctx):
    buildPath = computeBuildPath(ctx)
    gcovWrapper = os.path.join(ctx.path.abspath(), 'gcovWrapper.py')
    analyzer = CodeCoverageAnalyzer(buildPath, gcovWrapper)
    for currentDir, childDirs, files in os.walk(buildPath):
        print "Processing directory: ", currentDir
        if containCoverageData(files):
            with DirectoryScope(currentDir):
                analyzer.analyzeDirectory(currentDir)

    with DirectoryScope(buildPath):
        combinedCoverageFile = mergeInfoFiles(buildPath)
        generateCoverageReport(combinedCoverageFile)

def computeBuildPath(ctx):
	return os.path.abspath(os.path.join(ctx.path.abspath(), Context.out_dir))

class CodeCoverageAnalyzer(object):
    def __init__(self, buildRoot, gcovTool):
        self.buildRoot = os.path.abspath(buildRoot)
        self.gcovTool = gcovTool

    def analyzeDirectory(self, directory):
        directory = os.path.abspath(os.path.join(os.getcwd(), directory))
        infoFile = self.createCoverageInfoFile(directory)
        self.pruneCoverageInfoFile(infoFile)

    def createCoverageInfoFile(self, directory):
        outputFile = os.path.join(directory, "full_coverage.info")
        geninfo_command = "geninfo --gcov-tool {0} -o {1} -b {2} --no-recursion .".format(
            self.gcovTool, outputFile, self.buildRoot)
        runAndWait(geninfo_command)
        return outputFile

    def pruneCoverageInfoFile(self, fullInfoFile):
        codeCoveragePath = os.path.join(self.buildRoot, '*')
        outputFile = self.constructOutputFilePath(fullInfoFile)
        lcov_extract_command = 'lcov -o {0} -e {1} "{2}"'.format(outputFile, fullInfoFile, codeCoveragePath)
        runAndWait(lcov_extract_command)
        return outputFile

    def constructOutputFilePath(self, infoFile):
        return os.path.join(self.buildRoot, fileNameFromPath(infoFile))


def containCoverageData(files):
    return len([f for f in files if f.endswith('gcda')]) > 0

class DirectoryScope(object):
    def __init__(self, directory):
        self.directory = directory

    def __enter__(self):
        self.originalWorkingDir = os.getcwd()
        os.chdir(self.directory)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.originalWorkingDir)

def runAndWait(command):
    if subprocess.Popen(command, shell=True).wait():
        raise SystemExit(1)

def fileNameFromPath(filePath):
    directory, fileName = os.path.split(filePath)
    return directory.replace(os.sep, '_') + ".info"

def mergeInfoFiles(directory):
    infoFiles = fnmatch.filter(os.listdir(directory), '*.info')
    infoFiles = deleteZeroLengthFiles(infoFiles)
    outputFile = os.path.join(directory, 'coverage_result.info')
    lcov_merge_command = 'lcov -o {0} -a '.format(outputFile) + ' -a '.join(infoFiles)
    runAndWait(lcov_merge_command)
    return outputFile

def deleteZeroLengthFiles(files):
    nonEmptyFiles = []
    for f in files:
        if os.stat(f).st_size:
            nonEmptyFiles.append(f)
        else:
            os.remove(f)
    return nonEmptyFiles

def generateCoverageReport(infoFile):
    outputDirectory = 'coverage_report_' + str(int(time.time()*100))
    genhtml_command = 'genhtml -o {0} {1}'.format(outputDirectory, infoFile)
    runAndWait(genhtml_command)




