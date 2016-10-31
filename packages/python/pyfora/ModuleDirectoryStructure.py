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

"""Implements the class 'ModuleDirectoryStructure'"""

import re
import os
import glob

def markDeleted(path):
    base, name = os.path.split(os.path.abspath(path))
    newPath = os.path.join(base, ".%s.deleted" % name)
    if os.path.isdir(newPath):
        removeWholeDirectory(newPath)
    elif os.path.isfile(newPath):
        os.unlink(newPath)
    os.rename(path, newPath)


def removeWholeDirectory(path):
    """delete an entire directory and its children."""
    for p in os.listdir(path):
        fullName = os.path.join(path, p)
        if os.path.isdir(fullName):
            removeWholeDirectory(fullName)
        else:
            os.unlink(fullName)
    os.rmdir(path)

fileBlacklist = set([".DS_Store", ".git", "README", "CHANGELOG", "VERSION"])

def isBlacklisted(filename):
    if filename[0] == ".":
        # Ignore hidden files
        return True
    elif filename in fileBlacklist:
        # Ignore the explicitly blacklisted files
        return True
    return False

class ModuleDirectoryStructure(object):
    """code to model a 'module tree' and push/pull to the file system

    We model a module structure as a tree.  Every node in the tree has some
    text associated with it (the module definition) and a set of named
    submodules.

    We represent a module A on disk by writing its text in to 'A.fora', creating
    a directory called "A", and placing each of its submodules into "A".

    If a module has no submodules, we may omit the empty directory. We may
    also omit the .fora file, if the text is empty.
    """
    def __init__(self, ownText, subnodes):
        """initialize a ModuleDirectoryStructure

        ownText - a string of our own definition, or None
        subnodes - a dict from name to any submodules (which must have unique
            names). Submodules must be other ModuleDirectoryStructure
            objects.
        """
        self.ownText = ownText
        self.subnodes = subnodes
        self.extensionOverride = None
        for k in self.subnodes:
            assert isinstance(self.subnodes[k], ModuleDirectoryStructure)

    @staticmethod
    def fromJson(jsonRepr):
        res = ModuleDirectoryStructure(None, [])

        res.ownText = jsonRepr['ownText']
        res.subnodes = {x:ModuleDirectoryStructure.fromJson(jsonRepr['subnodes'][x]) for x in jsonRepr['subnodes']}
        res.extensionOverride = jsonRepr['extensionOverride']

        return res

    def toJson(self):
        return {
            'ownText': self.ownText,
            'subnodes': {x: self.subnodes[x].toJson() for x in self.subnodes},
            'extensionOverride': self.extensionOverride
            }

    def __str__(self):
        return "ModuleDirectoryStructure(%s)" % (str(self.ownText)[0:20] + "...",)
                #str(["%s:%s" % (str(key), str(value)) for key, value in self.subnodes.iteritems()]))

    def withRegexApplied(self, search, replace):
        """Returns a new MDS with a regex search and replace applied to all module text"""

        subdict = {}
        for name,subMds in self.subnodes.iteritems():
            subdict[name] = subMds.withRegexApplied(search, replace)

        return ModuleDirectoryStructure(
            re.sub(search, replace, self.ownText),
            subdict
            )

    @staticmethod
    def read(directoryPath, modulename, extension=None):
        """return an MDS initialized from the data in the file system

        directoryPath - string containing the name of the directory holding this
            module
        modulename - must be the name of the module.  Text should be in the file
            whose is with (modulename + "." + extension), and submodules should
            be in a directory named modulename.
        extension - a text extension (e.g. 'txt' or 'fora') to append to
            modulenames to indicate the locations of the text data component
            of a module.
            If None, all files of any extension are loaded.
        """

        newModuleText = ""
        newModuleSubmodules = {}

        subdirName = os.path.join(directoryPath, modulename)
        extensionOverride = None

        # If "A.fora" exists, open it.
        if extension is not None:
            if os.path.exists(subdirName + "." + extension):
                with open(subdirName + "." + extension, "rb") as f:
                    newModuleText = f.read()
        else:
            matches = glob.glob(subdirName + ".*")
            if len(matches) > 0:
                fileToOpen = matches[0]
                _, extensionOverride = os.path.splitext(fileToOpen)
                extensionOverride = extensionOverride[1:]

                with open(fileToOpen, "rb") as f:
                    newModuleText = f.read()


        # If folder "A/" (also) exists, recurse through it and gather all the children into
        # ModuleDirectoryStructures.
        if os.path.exists(subdirName):
            assert os.path.isdir(subdirName), "expected " + subdirName + " to be a directory."

            # List all the contents of the folder.
            for subname in sorted(os.listdir(subdirName)):
                if not isBlacklisted(subname) and (
                            os.path.isdir(os.path.join(subdirName, subname))
                            or (extension is not None and subname.endswith("." + extension))
                            or (extension is None)
                            ):
                    #pull off the extension if it's there
                    if extension is not None:
                        if subname.endswith("." + extension):
                            subname = subname[:-1 * (len(extension) + 1)]
                    elif extension is None and "." in subname:
                        _, ext = os.path.splitext(subname)
                        subname = subname[:-1 * (len(ext))] # No +1 here because splitext \
                                                                  # includes the dot.
                    #this module might have shown up twice (e.g. if there's
                    # "A" and "A.fora". we only want one copy...
                    if subname not in newModuleSubmodules:
                        newModuleSubmodules[subname] = (
                            ModuleDirectoryStructure.read(subdirName, subname, extension)
                            )

        mod = ModuleDirectoryStructure(newModuleText, newModuleSubmodules)
        if extension is None:
            mod.extensionOverride = extensionOverride
        return mod


    def pushToDisk(self, directoryPath, projectName, extension):
        """pushes this MDS into the file system.

        No files other than .fora files may exist below this one. So, this
        function deletes extra files it doesn't recognize.

        It will leave the system in a dirty state if any disk-related functions
        fail.
        """
        assert os.path.isdir(directoryPath), \
            " can't push to " + directoryPath + " as it's not a directory"

        subdir = os.path.join(directoryPath, projectName)

        #make sure its a directory, not a file
        if os.path.exists(subdir) and not os.path.isdir(subdir):
            os.unlink(subdir)

        if os.path.exists(subdir + "." + extension):
            os.unlink(subdir + "." + extension)

        # Save the module, yes, even if it's empty. Sometimes we need to save empty .fora files.
        with open(subdir + "." + extension, "wb") as f:
            f.write(self.ownText)

        expectedFiles = set()
        if len(self.subnodes):
            #we'll have to put something inside the directory
            if not os.path.exists(subdir):
                os.makedirs(subdir)

            for subname, submodule in self.subnodes.iteritems():
                expectedFiles.add(subname + '.' + submodule.extensionOverride)
                if len(submodule.subnodes):
                    expectedFiles.add(subname)
                submodule.pushToDisk(subdir, subname, submodule.extensionOverride)

        if os.path.exists(subdir):
            #make sure there's nothing in the directory with .fora that doesn't
            #belong there, but don't delete any directories that are not empty
            actualFiles = set(os.listdir(subdir))
            assert expectedFiles.issubset(actualFiles), \
                " some elements didn't save correctly: %s" % expectedFiles.difference(actualFiles)

            unexpectedFiles = [f for f in actualFiles - expectedFiles if not f.endswith('.deleted')]
            for unexpected in unexpectedFiles:
                fullpath = os.path.join(subdir, unexpected)
                markDeleted(fullpath)

