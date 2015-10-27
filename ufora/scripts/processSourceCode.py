#!/usr/bin/env python

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

"""processSourceCode.py

This file generates a copy of the BSA source code that doesn't contain any
cppml by applying cppml to each file in turn.

give it two args - a source directory and a destination directory.
"""

import os
import os.path
import sys
import tempfile

allfiles = []
endings = [".cpp",".cc", ".cppml", ".hppml", ".hpp", ".h", ".py", ".txt", ".fora", ".ypp", ".ttf", ".png"]

sourceDirectory = sys.argv[1]
targetDirectory = sys.argv[2]

pathToSRCDir = os.path.split(sourceDirectory)[0]

def walkFun(arg, dirname, fnames):
    for f in fnames:
        hasAnEnding = False
        for e in endings:
            if f.endswith(e):
                hasAnEnding = True

        if hasAnEnding:
            allfiles.append(os.path.join(dirname,f))

os.path.walk(sourceDirectory, walkFun, None)

#at this point, we have a list of all interesting files. run them through
#cppml if its necessary and write them to the corresponding "bsa_nocppml"
#directory

def sanitizedFilenameIncludeGuard(absFileName):
    """produce a string that matches the filename, but that's appropriate for use in a #include"""
    # Use relative path to ensure files are identical across build directories
    relFileName = os.path.relpath(absFileName)
    return "__CPPML_TRANSFORMED_" + "".join(['_' if not x.isalnum() else x for x in relFileName])

def targetFilename(f):
    assert f.startswith(sourceDirectory)
    return targetDirectory + f[len(sourceDirectory):]

def writeCppmlInclude():
    cppmlSrcDir = os.path.join(os.path.split(sourceDirectory)[0],"cppml","include","cppml")
    cppmlDestDir = os.path.join(os.path.split(targetDirectory)[0],"cppml","include","cppml")

    if not os.path.exists(cppmlDestDir):
        os.makedirs(cppmlDestDir)

    for f in os.listdir(cppmlSrcDir):
        data = open(os.path.join(cppmlSrcDir,f),"r").read()
        targetPath = os.path.join(cppmlDestDir,f)
        if not os.path.exists(targetPath) or open(targetPath,"r").read() != data:
            open(targetPath,"w").write(data)

writeCppmlInclude()

for f in allfiles:
    if f.endswith(".ypp"):

        with tempfile.NamedTemporaryFile() as tempFile:
            name = tempFile.name
            tempFile.close()

            cmdResult = os.popen("bison " + f + " -o " + name).read()
            assert cmdResult == ""
            data = open(name, "r").read()


        fileRoot = f[:-4]
        origFileExtension = f[-3:]
        newFileExtension = "cpp"
        f = fileRoot + "_" + origFileExtension + "." + newFileExtension
    elif f.endswith(".cppml") or f.endswith(".hppml"):
        pathToCPPML = os.path.join(pathToSRCDir, "cppml","cppml")

        print pathToCPPML + " " + f + " --guarded-preamble:"
        data = os.popen(pathToCPPML + " " + f + " --guarded-preamble").read()
        #modify the filename
        fileRoot = f[:-6]
        origFileExtension = f[-5:]
        newFileExtension = origFileExtension[:-2]	#cpp or hpp, dropping the 'ml'
        f = fileRoot + "_" + origFileExtension + "." + newFileExtension

    else:
        data = open(f, "r").read()

    if f.endswith(".cpp") or f.endswith(".hpp"):
        data = data.replace('.hppml"', '_hppml.hpp"')
        guardName = sanitizedFilenameIncludeGuard(f)
        data = "#ifndef %s\n#define %s\n%s\n\n#endif %s\n" % (guardName, guardName, data, guardName)

    f = targetFilename(f)
    #now write to disk

    #fist make sure the path is there
    if not os.path.exists(os.path.split(f)[0]):
        os.makedirs(os.path.split(f)[0])

    #see if we don't need to write the data
    writeData = True
    try:
        existingData = open(f, "r").read()
        if data == existingData:
            writeData = False
    except:
        pass
    #now write the data
    if writeData:
        print "Wrote data to ", f
        open(f, "w").write(data)


