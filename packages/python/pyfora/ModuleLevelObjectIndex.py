import sys
import os
import logging

singleton = [None]

class NamedObjectNotFoundAsModuleLevelObject:
    """A singleton instance used as a token to indicate that we couldn't find the object."""
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return "NamedObjectNotFoundAsModuleLevelObject(%s)" % (self.path,)

    def __str__(self):
        return repr(self)

class ModuleLevelObjectIndex(object):
    """Indexes all the objects that are accessible from modules in sys.modules"""
    def __init__(self):
        self.modulesVisited = set()
        self.module_objects_by_name = {}
        self.modules_and_names_by_object = {}
        self.size_of_sys_at_last_load = 0

        self.loadModules()

    def loadModules(self):
        if len(sys.modules) != self.size_of_sys_at_last_load:
            self.size_of_sys_at_last_load = len(sys.modules)
            for modulename, module in dict(sys.modules).iteritems():
                self.loadModule(modulename, module)

    def loadModule(self, modulename, module):
        if modulename in self.modulesVisited:
            return
        self.modulesVisited.add(modulename)

        #ignore all modules that are not part of the base python installation.
        #this is a crude way of deciding which modules are going to be available
        #on both the host and the server.
        if modulename not in sys.builtin_module_names and (
                not hasattr(module, '__file__') or not os.path.abspath(module.__file__).startswith(sys.prefix)
                ):
            return

        if module is not None:
            d = dict(module.__dict__)
            for leafItemName, leafItemValue in d.iteritems():
                self.module_objects_by_name["modules", modulename, leafItemName] = leafItemValue
                self.modules_and_names_by_object[id(leafItemValue)] = ("modules", modulename, leafItemName)
            self.modules_and_names_by_object[id(module)] = ("modules", modulename)
            self.module_objects_by_name["modules", modulename] = module

    def getPathToObject(self, obj, ifNotFound=None):
        self.loadModules()
        return self.modules_and_names_by_object.get(id(obj), ifNotFound)

    def getObjectFromPath(self, path):
        if path is not None and len(path) > 1 and path[0] == 'modules':
            if path[1] not in self.modulesVisited:
                self.importModule(path[1])

        if path not in self.module_objects_by_name:
            return NamedObjectNotFoundAsModuleLevelObject(path)

        return self.module_objects_by_name[path]

    def importModule(self, moduleName):
        try:
            module = __import__(moduleName)
            self.loadModule(moduleName, module)
        except ImportError:
            self.modulesVisited.add(moduleName)
            return

    @staticmethod
    def singleton():
        if singleton[0] is None:
            singleton[0] = ModuleLevelObjectIndex()
        return singleton[0]
