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

import importlib
import sys


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

            try:
                pure_module = importlib.import_module("pyfora.pure_modules.pure_%s" % root)
                self.load_pure_module(pure_module)
                self.already_loaded.add(root)
            except ImportError:
                pass
        self.last_seen_sys_modules_len = len(sys.modules)

    def load_pure_module(self, module):
        for mapping in module.generateMappings():
            self.addMapping(mapping)
