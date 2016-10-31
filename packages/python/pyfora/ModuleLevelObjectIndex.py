import sys
import os

singleton = [None]

class ModuleLevelObjectIndex(object):
    """Indexes all the objects that are accessible from modules in sys.modules"""
    def __init__(self):
        self.modulesVisited = set()
        self.module_objects_by_name = {}
        self.modules_and_names_by_object = {}

        self.loadModules()

    def loadModules(self):
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

    def getPathToObject(self, obj, ifNotFound=None):
        return self.modules_and_names_by_object.get(id(obj), ifNotFound)


    def getObjectFromPath(self, path, ifNotFound=None):
        return self.module_objects_by_name.get(path, ifNotFound)

    @staticmethod
    def singleton():
        if singleton[0] is None:
            singleton[0] = ModuleLevelObjectIndex()
        return singleton[0]
