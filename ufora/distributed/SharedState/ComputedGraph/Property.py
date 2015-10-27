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

"""CGSS.Property provides a simple wrapper around SharedState for use within ComputedGraph.

class X(ComputedGraph.Location):
    shared = CGSS.Property.Property(
        subspaceFunction = lambda self: self.sharedStateSubspace,
        default = lambda: ... ,
        validator = lambda x: ...
        )

now, "shared" will be a property held in SharedState.

subspaceFunction should return a ComputedGraph.Subspace object. This subspace will be sliced
into by the property name, and that resulting subspace will hold the value.
"""


import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.distributed.SharedState.ComputedGraph.SynchronousPropertyAccess as SynchronousPropertyAccess

def Property(	subspaceFunction = lambda instance: instance.sharedStateSubspace,
                default = lambda: None,
                exposeToProtocol = False
                ):
    """Produce a property in a ComputedGraph location that's tied to a value in SharedState.

    documentGetter - a function that takes the ComputedGraph location instance and
        produces an object to be used as a key in the shared state keyspace.
    default - a factory producing default values to use if the node is unpopulated or not yet loaded.
    validator - a function that's called to sanitize values in the database. This allows
        us to react properlty to bad data that might have been placed in SharedState.
        This function will be called on every value coming _out_ of the property,
        and its return value is the one we actually present to clients.
    """
    def propertyListGenerator(name, cls):
        """Generates a list of (name, ComputedGraph.Property) objects corresponding to
        this property object."""

        memo = dict()

        def propertyValueFromNodeGetter(instance):
            """Get the actual property value from an instance.

            instance - a ComputedGraph location that the property is tied to.
            """

            subspace = nodeGetter(instance)

            if SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None:
                if not subspace.loaded:
                    subspace.keyspace.waitLoaded()
            else:
                subspace.keyspace.ensureSubscribed()

            val = subspace.value

            if val is None:
                return default()

            return val[0]

        def propertyValueFromNodeSetter(instance, val):
            """Set the property value 'name' in instance 'instance' to 'val'

            We must be in 'synchronous' mode for this to work.  We'll load the
            keyspace if its not loaded.
            """

            subspace = nodeGetter(instance)

            if SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None:
                if not subspace.loaded:
                    subspace.keyspace.waitLoaded()

            if subspace.value != (val,):
                subspace.value = (val,)

        def nodeGetter(instance):
            """Produces a CGSS.Node.Node object corresponding to this property's value.

            We use the hash of the result of the documentGetter function to decide which keyspace
            we want to use, and then we hash the pair (instance, name) to decide which key
            to use.
            """
            if (instance, name) not in memo:
                subspace = subspaceFunction(instance)

                if subspace is None:
                    assert False, "Instance %s produced an empty subspace" % instance

                memo[(instance,name)] = subspace.subspace(name)
            return memo[(instance,name)]

        return [
            (name, ComputedGraph.Property(propertyValueFromNodeGetter,propertyValueFromNodeSetter))
            ]

    return ComputedGraph.PropertyMaker(propertyListGenerator, exposeToProtocol)



