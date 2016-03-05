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

import imp
import importlib
import os
import sys

from pyfora.PureImplementationMapping import PureMappingRegistry


def typeOfInstance(i):
    try:
        return i.__class__
    except AttributeError:
        return type(i)

class PureImplementationMappings(object):
    """Collection of PureImplementationMapping objects"""
    def __init__(self):
        self.last_seen_sys_modules_len = 0
        self.already_loaded = set()
        self.mappings = []
        self.pythonTypeToMapping = {}
        self.pyforaTypeToMapping = {}
        self.pythonInstanceIdsToMappingAndId = {}

    def addMapping(self, mapping):
        self.mappings.append(mapping)
        for mappableType in mapping.getMappablePythonTypes():
            self.pythonTypeToMapping[mappableType] = mapping
        for purePythonType in mapping.getPurePythonTypes():
            self.pyforaTypeToMapping[purePythonType] = mapping
        for instance in mapping.getMappableInstances():
            self.pythonInstanceIdsToMappingAndId[id(instance)] = (mapping, instance)

    def canMap(self, instance):
        self.load_pure_modules()
        return (
            typeOfInstance(instance) in self.pythonTypeToMapping or
            id(instance) in self.pythonInstanceIdsToMappingAndId
            )

    def canInvert(self, instance):
        return typeOfInstance(instance) in self.pyforaTypeToMapping

    def mappableInstanceToPure(self, instance):
        if id(instance) in self.pythonInstanceIdsToMappingAndId:
            mapper = self.pythonInstanceIdsToMappingAndId[id(instance)][0]
        else:
            mapper = self.pythonTypeToMapping[typeOfInstance(instance)]
        return mapper.mapPythonInstanceToPyforaInstance(instance)

    def pureInstanceToMappable(self, instance):
        mapper = self.pyforaTypeToMapping[typeOfInstance(instance)]
        return mapper.mapPyforaInstanceToPythonInstance(instance)


    def load_pure_modules(self):
        if len(sys.modules) <= self.last_seen_sys_modules_len:
            return

        loaded_modules = sys.modules.keys()
        loaded_root_modules = set(m.split('.')[0] for m in loaded_modules)
        for root in loaded_root_modules:
            if root in self.already_loaded or root == 'pyfora':
                continue

            self.try_load_pure_module(root)
        self.last_seen_sys_modules_len = len(sys.modules)

    def addMappingsForModule(self, module_name):
        for mapping in PureMappingRegistry.mappingsForRootModule(module_name):
            self.addMapping(mapping)
        self.already_loaded.add(module_name)


    def try_load_pure_module(self, module_name):
        try:
            # first try to load a pyfora pure module, if one exists
            importlib.import_module("pyfora.pure_modules.pure_" + module_name)
            self.addMappingsForModule(module_name)
        except ImportError:
            pass

        pyfora_path = os.getenv('PYFORAPATH')
        if pyfora_path is None:
            return

        for mod in [module_name, "pure_" + module_name]:
            path = os.path.join(pyfora_path, mod)
            if os.path.exists(path) or os.path.exists(path + '.py'):
                try:
                    load_args = imp.find_module(mod, pyfora_path)
                    imp.load_module("pyfora.user_pure_modules.pure_" + mod, *load_args)
                    self.addMappingsForModule(module_name)
                except ImportError:
                    pass

