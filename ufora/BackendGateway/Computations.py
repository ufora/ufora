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

import itertools
import threading

from ufora.BackendGateway import tuple_it
from ufora.BackendGateway.Observable import Observable, observable
import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.Cumulus as CumulusNative



class ComputationCumulusState(Observable):
    def __init__(self, cumulus_id):
        super(ComputationCumulusState, self).__init__()
        self.cumulus_id = cumulus_id
        self._result_and_stats = None
        self.status = None
        self._cpu_assignments = None
        self._progress_stats = None
        self.is_started = None


    @property
    def comp_id(self):
        return tuple_it(self.cumulus_id.toSimple())


    @property
    def result_and_stats(self):
        return self._result_and_stats


    @result_and_stats.setter
    @observable
    def result_and_stats(self, value):
        self._result_and_stats = value


    @property
    def cpu_assignments(self):
        return self._cpu_assignments


    @cpu_assignments.setter
    @observable
    def cpu_assignments(self, value):
        self._cpu_assignments = value




class Computations(object):
    def __init__(self, cumulus_gateway, cache_loader, object_converter):
        self.cumulus_gateway = cumulus_gateway
        self.cache_loader = cache_loader
        self.object_converter = object_converter

        self.lock_ = threading.RLock()
        self.computation_states = {}
        self.comp_ids_to_cumulus_ids = {}
        self.priority_allocator = itertools.count()
        self.cumulus_gateway.onComputationResult = self.on_computation_result
        self.cumulus_gateway.onCPUCountChanged = self.on_cpu_count_changed


    def create_computation(self, state):
        cumulus_id = state.cumulus_id
        comp_id = state.comp_id
        with self.lock_:
            if cumulus_id not in self.computation_states:
                self.computation_states[cumulus_id] = state
                self.comp_ids_to_cumulus_ids[comp_id] = cumulus_id


    def start_computation(self, cumulus_id):
        with self.lock_:
            state = self.computation_states.get(cumulus_id)
            assert state is not None, "Computation doesn't exist: %s" % cumulus_id

            if state.is_started:
                return

            state.is_started = True
        self.cumulus_gateway.setComputationPriority(
            cumulus_id,
            CumulusNative.ComputationPriority(self.priority_allocator.next())
            )


    def is_started(self, cumulus_id):
        return (cumulus_id in self.computation_states
                and self.computation_states[cumulus_id].is_started)


    def cumulus_id_for_definition(self, computation_definition):
        return self.cumulus_gateway.getComputationIdForDefinition(computation_definition)


    def bytecount_for_big_vectors(self, big_vectors_hashset):
        return self.cumulus_gateway.bytecountForBigvecs(big_vectors_hashset)


    def cancel(self, cumulus_id):
        # TODO: implement...
        return True


    def cancel_all(self):
        with self.lock_:
            for cumulus_id, refcount in self.refcount_by_cumulus_id.iteritems():
                if refcount > 0:
                    self.cumulus_gateway.setComputationPriority(
                        cumulus_id,
                        CumulusNative.ComputationPriority()
                        )
                    self.refcount_by_cumulus_id[cumulus_id] = 0

            self.cumulus_gateway.resetStateCompletely()


    def get_computation_state(self, comp_id):
        return self.computation_states.get(
            self.comp_ids_to_cumulus_ids.get(comp_id)
            )


    def on_computation_result(self, cumulus_id, result, statistics):
        with self.lock_:
            state = self.computation_states.get(cumulus_id)
        state.result_and_stats = (result, statistics)


    def on_cpu_count_changed(self, computation_cpu_assignments):
        cumulus_id = computation_cpu_assignments.computation
        with self.lock_:
            computation_state = self.computation_states.get(cumulus_id)
        if computation_state is None:
            return
        computation_state.cpu_assignments = computation_cpu_assignments


    def create_apply_tuple(self, arg_ids):
        def unwrap(arg):
            if isinstance(arg, int):
                return self.object_converter.converted_objects[arg]
            else:
                return arg

        impl_vals = tuple(unwrap(arg) for arg in arg_ids)
        return impl_vals[:1] + (ForaValue.FORAValue.symbol_Call.implVal_,) + impl_vals[1:]
