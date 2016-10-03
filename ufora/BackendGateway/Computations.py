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
import logging
import threading

import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.Cumulus as CumulusNative
import ufora.native.FORA as ForaNative

from pyfora.Future import Future


ImplValContainer_ = ForaNative.ImplValContainer


class Computations(object):
    def __init__(self, cumulus_gateway, cache_loader, object_converter):
        self.cumulus_gateway = cumulus_gateway
        self.cache_loader = cache_loader
        self.object_converter = object_converter

        self.lock_ = threading.RLock()
        self.pending_computations = {}
        self.priority_allocator = itertools.count()
        self.cumulus_gateway.onComputationResult = self.on_computation_result


    def create_computation(self, arg_ids):
        apply_tuple = self.create_apply_tuple(arg_ids)
        logging.info("apply tuple: %s", apply_tuple)
        comp_id = self.cumulus_gateway.getComputationIdForDefinition(
            self.create_computation_definition(apply_tuple)
            )
        with self.lock_:
            logging.info("adding computation: %s", comp_id)
            self.pending_computations[comp_id] = None

        return comp_id


    def start_computation(self, comp_id):
        with self.lock_:
            logging.info("Pending computations: %s", self.pending_computations)
            if comp_id not in self.pending_computations:
                # TODO: error - computation wasn't created
                logging.error("Computation doesn't exist: %s", comp_id)

            future = self.pending_computations[comp_id]
            if future:
                return future

            future = Future(lambda: self.cancel(comp_id))

            self.pending_computations[comp_id] = future
            logging.info("Setting computation priority")
            self.cumulus_gateway.setComputationPriority(
                comp_id,
                CumulusNative.ComputationPriority(self.priority_allocator.next())
                )
            logging.info("Computation priority set")
        return future


    def cancel(self, comp_id):
        # TODO: implement...
        return True


    def cancel_all(self):
        with self.lock_:
            for comp_id, refcount in self.refcount_by_comp_id.iteritems():
                if refcount > 0:
                    self.cumulus_gateway.setComputationPriority(
                        comp_id,
                        CumulusNative.ComputationPriority()
                        )
                    self.refcount_by_comp_id[comp_id] = 0

            self.cumulus_gateway.resetStateCompletely()


    def on_computation_result(self, comp_id, result, statistics):
        logging.info("Computation result: %s", comp_id)
        with self.lock_:
            future = self.pending_computations.get(comp_id)
            del self.pending_computations[comp_id]
        future.set_result((result, statistics))


    def create_apply_tuple(self, arg_ids):
        logging.info("arg ids: %s", arg_ids)
        def unwrap(arg):
            if isinstance(arg, int):
                logging.info("converted objects: %s", self.object_converter.converted_objects)
                return self.object_converter.converted_objects[arg]
            else:
                return arg

        impl_vals = tuple(unwrap(arg) for arg in arg_ids)
        logging.info("impl vals: %s", impl_vals)
        return impl_vals[:1] + (ForaValue.FORAValue.symbol_Call.implVal_,) + impl_vals[1:]


    @staticmethod
    def create_computation_definition(apply_tuple):
        terms = []

        for a in apply_tuple:
            if isinstance(a, (long, int, str, bool)):
                terms.append(
                    CumulusNative.ComputationDefinitionTerm.Value(ImplValContainer_(a),
                                                                  None)
                    )
            elif isinstance(a, ImplValContainer_):
                terms.append(CumulusNative.ComputationDefinitionTerm.Value(a, None))
            else:
                terms.append(a.computationDefinitionTerm_)

        return CumulusNative.ComputationDefinition.Root(
            CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(terms)
            )
