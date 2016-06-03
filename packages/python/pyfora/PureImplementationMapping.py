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

import inspect
import pyfora.Exceptions as Exceptions

class PureImplementationMapping(object):
    """Plugin base to allow pyfora to convert user-defined types like dataframes to pyfora and back.

    This infrastructure allows us to provide alternative implementations of
    libraries that are implemented in ways that the pyfora system cannot
    convert (e.g. numpy).

    In this model, 'mappable' types are the regular python types (like numpy
    array, dataframe, etc.) that we want to map, and 'pure' types are their
    images in pure-python. """

    def getMappablePythonTypes(self):
        """Return the python type that this mapping knows how to convert.

        This should return a list of python types and classes. Any time the
        converter sees an instance of one of these types, Pyfora will invoke
        this class to provide an alternate, translatable form of the instance.
        """
        #subclasses should implement
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.getMappablePythonTypes.__name__,
               type(self).__name__)
            )

    def getMappableInstances(self):
        """Return a list of specific instances this mapper knows how to convert."""
        #subclasses should implement
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.getMappableInstances.__name__,
               type(self).__name__)
            )

    def getPurePythonTypes(self):
        """Return the pure-python type that this mapping converts to.

        This should return a list of python classes that this mapper knows how to invert.
        """
        #subclasses should implement
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.getPurePythonTypes.__name__,
               type(self).__name__)
            )

    def mapPythonInstanceToPyforaInstance(self, instance):
        """Given an instance of the mappable class, return an instance implementing it in pure-python."""
        # subclasses should implement
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.mapPythonInstanceToPyforaInstance.__name__,
               type(self).__name__)
            )

    def mapPyforaInstanceToPythonInstance(self, instance):
        """Given an instance of the pure-python class, return an instance of the mappable type."""
        # subclasses should implement
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.mapPyforaInstanceToPythonInstance.__name__,
               type(self).__name__)
            )

class InstanceMapping(PureImplementationMapping):
    """Mapping infrastructure to convert singleton instances to PurePython class instances.

    This mapping is primarily used to map builtins like 'len' to instances of pure-python classes like
    pyfora.pure_modules.pure___builtin__.Len.
    """
    def __init__(self, instance, pureClass):
        self.instance = instance
        self.pureClass = pureClass

    def getMappablePythonTypes(self):
        return []

    def getMappableInstances(self):
        return [self.instance]

    def getPurePythonTypes(self):
        return [self.pureClass]

    def mapPythonInstanceToPyforaInstance(self, instance):
        assert instance is self.instance
        if self.pureClass is None:
            raise Exceptions.PyforaNotImplementedError(
                "conversion of '%s' not yet implemented" %
                (instance.__name__ if hasattr(instance, "__name__") else instance))
        return self.pureClass()

    def mapPyforaInstanceToPythonInstance(self, instance):
        assert instance.__class__ is self.pureClass
        return self.instance


class PureMappingRegistry(object):
    mappings = {}

    @classmethod
    def mappingsForRootModule(cls, root):
        return cls.mappings.get(root, [])


def pureMapping(instance_or_mapping, module=None):
    def registerMapping(root_module, mapping):
        mappings = PureMappingRegistry.mappings.get(root_module)
        if mappings is None:
            mappings = []
            PureMappingRegistry.mappings[root_module] = mappings
        mappings.append(mapping)

    if inspect.isclass(instance_or_mapping) and issubclass(instance_or_mapping,
                                                           PureImplementationMapping):
        root_module = instance_or_mapping.__module__.split('.')[-1]
        if root_module.startswith('pure_'):
            root_module = root_module[len('pure_'):]
        registerMapping(root_module, instance_or_mapping())
        return instance_or_mapping

    if module is None:
        if hasattr(instance_or_mapping, '__module__'):
            module = instance_or_mapping.__module__
        elif hasattr(instance_or_mapping, '__class__'):
            module = instance_or_mapping.__class__.__module__

    assert module is not None, "Using @pureMapping with unsupported object %s" % (
        instance_or_mapping,)

    def wrap(cls):
        root_module = module.split('.')[0]
        registerMapping(root_module, InstanceMapping(instance_or_mapping, cls))
        return cls
    return wrap
