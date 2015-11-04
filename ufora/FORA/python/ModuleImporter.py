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

"""module.py

Code to read and write FORA modules to and from disk.

A FORA module is a file (ending in .fora), a directory with some .fora files
within it (each of which is a member of themodule), or both.

FORA modules may be nested.  A directory that's a module must have a
corresponding .fora file, even if it's empty.

FORA modules may depend on each other purely by member access. That is, if you
have 'module1' and 'module2' in your FORA path, 'module1' may refer to 'module2'
or vice versa.  Modules may not refer to each other circularly. If they do,
they're really part of the same module...

"""

import logging
import os
import os.path

import ufora.config.Setup as Setup
import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure
import ufora.FORA.python.ErrorFormatting as ErrorFormatting
import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.ParseException as ParseException

import ufora.native.FORA as ForaNative


#some constants we need
symbol_Call_ = ForaNative.symbol_Call
symbol_package = ForaNative.makeSymbol("package")
symbol_member = ForaNative.makeSymbol("member")

#exceptions we throw
class FORAImportException(Exception):
    def __init__(self):
        Exception.__init__(self)
    def __str__(self):
        return "FORA import error"

class FORAImportRuntimeException(FORAImportException):
    def __init__(self, foraException):
        FORAImportException.__init__(self)
        self.foraException = foraException
    def __str__(self):
        return "ImportError: " + str(self.foraException)

class FORACircularImportException(FORAImportException):
    def __init__(self, paths):
        FORAImportException.__init__(self)
        self.paths = paths
    def __str__(self):
        return (
            "Circular FORA Module dependencies:\n\t"
                + "\n\t".join(self.paths)
                + "\n\t"
                )

#a dict from paths to circular import groups
def importModuleFromPath(p,
                    searchForFreeVariables = False,
                    allowPrivate = False,
                    moduleImportParentList = None,
                    pathToCodeDefinitionStrings = lambda path: ["ModuleImporter", path]
                    ):
    """return a ImplValContainer for the module object at path 'p' or raise
    an FORAImportException.

    p - a string containing a path to the directory or file containing the
        module
    searchForFreeVariables - boolean indicating whether to search the FORA path
        for modules whenever a free variable is encountered
    allowPrivate - a boolean indicating whether private symbols (e.g. `` symbols)
        are allowed. These symbols wrap unsafe FORA operations that client code
        should never call. Only the builtins module should have access to these
    moduleImportParentList - None, or a list of paths showing the current
        module search path. if a module shows up twice, then we have circular
        module references and we'll throw an exception
    """

    if moduleImportParentList is None:
        moduleImportParentList = ()

    if p in moduleImportParentList:
        #this is a circular module import
        raise FORACircularImportException(moduleImportParentList + (p,))

    moduleImportParentList = moduleImportParentList + (p,)

    directory, fname = os.path.split(p)
    if fname.endswith(".fora"):
        fname = fname[:-5]
    mds = ModuleDirectoryStructure.ModuleDirectoryStructure.read(directory, fname, "fora")

    return importModuleFromMDS(
        mds,
        directory,
        fname,
        searchForFreeVariables,
        allowPrivate,
        moduleImportParentList,
        pathToCodeDefinitionStrings
        )

#a dict from paths to circular import groups
def importModuleFromMDS(
                    mds,
                    directory,
                    fname,
                    searchForFreeVariables = False,
                    allowPrivate = False,
                    moduleImportParentList = None,
                    pathToCodeDefinitionStrings = lambda path: ["ModuleImporter", path]
                    ):
    if moduleImportParentList is None:
        moduleImportParentList = ()

    importExpr, memberType = convertMDSToCreateObjectExpression(
                        mds,
                        os.path.join(directory, fname),
                        allowPrivate,
                        fname,
                        pathToCodeDefinitionStrings
                        )

    freeVars = importExpr.freeVariables
    freeVarDefs = {}

    if searchForFreeVariables:
        for f in freeVars:
            freeVarDefs[f] = importModuleAndMemberByName(f, moduleImportParentList)

    for f in freeVars:
        if f not in freeVarDefs or freeVarDefs[f] is None:
            codeLocation = importExpr.computeFreeVariableLocations(f)[0]

            raise ParseException.ParseException(
                ForaNative.FunctionParseError(
                    "Couldn't resolve free variable '%s'" % f,
                    codeLocation.range
                    ),
                codeLocation.defPoint
                )

    parser = ForaNative.ModuleParser()

    result = parser.bind(importExpr, freeVarDefs, False)

    assert result.isModule()
    assert result.asModule.result is not None

    return result.asModule.result

def convertMDSToSourceCodeTree(mds, name):
    children = []

    if name.endswith(".script"):
        name = name[:-7]
        return ForaNative.SourceCodeTree.Script(name, mds.ownText)

    for subnodeName in mds.subnodes:
        children.append(convertMDSToSourceCodeTree(mds.subnodes[subnodeName], subnodeName))

    if mds.ownText:
        return ForaNative.SourceCodeTree.Module(name, mds.ownText, children)
    else:
        return ForaNative.SourceCodeTree.Module(name, children)


def convertMDSToCreateObjectExpression(mds, path, allowPrivate, name, pathToCodeDefinitionStrings):
    """given an MDS and a path, return an expression
    that creates a module member and the type of module member."""

    tree = convertMDSToSourceCodeTree(mds, name)

    parser = ForaNative.ModuleParser()

    result = parser.parse(
        tree,
        allowPrivate,
        ForaNative.CodeDefinitionPoint.ExternalFromStringList(
            pathToCodeDefinitionStrings(path)
            )
        )

    if len(result.errors) == 0:
        return result, symbol_package

    error = result.errors[0]

    raise ParseException.ParseException(
        ForaNative.FunctionParseError(
            error.error,
            error.location.range
            ),
        error.location.defPoint
        )

def importModuleByName(modulename, moduleImportParentList = None):
    result = importModuleAndMemberByName(modulename, moduleImportParentList)
    if result is not None:
        if result[1] is not None:
            import ufora.FORA.python.FORA as FORA
            return getattr(ForaValue.FORAValue(result[0]), result[1]).implVal_
        else:
            return result[0]
    else:
        return None


def importModuleAndMemberByName(modulename, moduleImportParentList = None):
    """search for a globally named object 'modulename' and return it.

    First, we search the builtin module. If it's not found there, we then
    check the FORA path. If it's not found there, we return None.

    If we don't return None, we return a native ImplValContainer
    """
    logging.debug("Importing module %s", modulename)

    if modulename in modulesByName_:
        return (modulesByName_[modulename], None)
    if modulename == "builtin":
        return (builtinModuleImplVal(), None)
    if modulename in builtinModuleMembers():
        return (builtinModuleImplVal(), modulename)
    else:
        #search the FORA path for a module
        for root in foraPath:
            fullpath = os.path.join(root, modulename + ".fora")
            if os.path.isfile(fullpath):
                #attempt to import this module.
                modulesByName_[modulename] = importModuleFromPath(
                        fullpath,
                        searchForFreeVariables = True,
                        allowPrivate = False,
                        moduleImportParentList = moduleImportParentList
                        )
                return (modulesByName_[modulename], None)

def getSubModuleNames(moduleForaVal):
    import ufora.FORA.python.FORA as FORA
    tr = []
    members = FORA.objectMembers(moduleForaVal)

    for member, memberMeta in members.iteritems():
        if memberMeta == FORA.symbol_package:
            tr.append(member)

    return tr

def moduleImporterPathToFilenameAndCode(elts):
    """given a list of strings (from a CodeLocation::External) return the filename
    and file data associated with them, or return None"""

    path = os.path.abspath(os.path.join(*elts))

    if os.path.isfile(path + ".fora"):
        path = path + ".fora"
    elif os.path.isfile(path + ".script.fora"):
        path = path + ".script.fora"
    else:
        return None

    with open(path, "rb") as f:
        return path, f.read()

    if len(elts) == 1 and os.path.isfile(elts[0]):
        with open(elts[0], "rb") as f:
            return elts[0], f.read()

#TODO anybody refactor The list of absolute pathnames to directories we can search for FORA modules
#TODO anybody refactor This needs to come from config!

foraPath = [os.path.abspath('.')]

foraPathEnvVariable_ = os.getenv("FORAPATH")
if foraPathEnvVariable_ is not None:
    foraPath += foraPathEnvVariable_.split(":")

#all the modules we've imported so far, except for the builtin module itself
modulesByName_ = {}

def registerModuleByName(name, moduleValue):
    """registers a value as a globally reachable object in FORA

    moduleValue can be anything - if convertable to a python object, it will be
    """
    modulesByName_[name] = ForaValue.FORAValue(moduleValue).implVal_


_curDir = os.path.split(os.path.abspath(__file__))[0]


_builtinModuleMembers = None
def builtinModuleMembers():
    global _builtinModuleMembers
    if _builtinModuleMembers is None:
        raise Setup.InitializationException("ModuleImporter is not initialized")
    return _builtinModuleMembers

_builtinModuleImplVal = None
def builtinModuleImplVal():
    global _builtinModuleImplVal
    if _builtinModuleImplVal is None:
        raise Setup.InitializationException("ModuleImporter is not initialized")
    return _builtinModuleImplVal

_builtinPath = None
def initialize(setupObjectToUse = None, reimport = False):
    global _builtinModuleMembers, _builtinModuleImplVal, _builtinPath
    if _builtinModuleMembers is not None and not reimport:
        return

    if setupObjectToUse is None:
        setupObjectToUse = Setup.currentSetup()

    try:
        _builtinPath = os.path.abspath(os.path.join(_curDir, "..","builtin"))

        def pathToCodeDefinitionStrings(path):
            return ["Builtins", os.path.relpath(path, os.path.join(_builtinPath, ".."))]

        _builtinModuleImplVal = importModuleFromPath(
            _builtinPath,
            allowPrivate = True,
            pathToCodeDefinitionStrings = pathToCodeDefinitionStrings
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

    _builtinModuleMembers = _builtinModuleImplVal.objectMembers

    logging.info("Initialized ModuleImporter with builtin hash of '%s'", hash(_builtinModuleImplVal))

def pathToBuiltins():
    return _builtinPath

def builtinPathToFilenameAndCode(elts):
    """given a list of strings (from a CodeLocation::External) return the filename
    and file data associated with them, or return None"""

    global _builtinPath

    path = os.path.abspath(os.path.join(*[_builtinPath, ".."] + elts))

    if os.path.isfile(path + ".fora"):
        path = path + ".fora"
    elif os.path.isfile(path + ".script.fora"):
        path = path + ".script.fora"
    else:
        return None

    with open(path, "rb") as f:
        return path, f.read()


ErrorFormatting.exceptionCodeSourceFormatters["ModuleImporter"] = (
        moduleImporterPathToFilenameAndCode
        )
ErrorFormatting.exceptionCodeSourceFormatters["Builtins"] = (
        builtinPathToFilenameAndCode
        )


