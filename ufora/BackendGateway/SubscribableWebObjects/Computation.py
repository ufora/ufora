#   Copyright 2015-2016 Ufora Inc.
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


import logging
import uuid

from ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaToJsonTransformer \
    import PyforaToJsonTransformer
from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedFunction, ExposedProperty, observable
import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.FORA as ForaNative



class ComputationState(object):
    def __init__(self, args):
        self.args = args
        self.computation_definition = None
        self.result = None
        self.status = None
        self.stats = None
        self.json_result = None
        self.comp_id = None
        self._cumulus_id = None


    @property
    def cumulus_id(self):
        return self._cumulus_id


    @cumulus_id.setter
    def cumulus_id(self, value):
        self._cumulus_id = value
        self.comp_id = self._cumulus_id.toSimple()



class Computation(SubscribableObject):
    def __init__(self, id, cumulus_env, args):
        super(Computation, self).__init__(id, cumulus_env)
        comp_id = args.get('comp_id')
        logging.info("New computation with comp_id: %s", comp_id)
        self._state = (
            ComputationState(args) if comp_id is None
            else self.computations.get_computation_state(comp_id)
            )


    @ExposedProperty
    def computation_id(self):
        return self._state.comp_id


    @ExposedProperty
    def computation_status(self):
        return self._state.status


    @computation_status.setter
    @observable
    def computation_status(self, value):
        self._state.status = value


    @ExposedProperty
    def stats(self):
        return self._state.stats


    @stats.setter
    @observable
    def stats(self, value):
        self._state.stats = value


    @ExposedProperty
    def result(self):
        return self._state.json_result


    @result.setter
    @observable
    def result(self, value):
        self._state.json_result = value


    @ExposedFunction
    def start(self, _):
        future = self.computations.start_computation(self.cumulus_id)
        future.add_done_callback(self.on_computation_result)
        return True


    @ExposedFunction
    def request_result(self, max_byte_count):
        import pyfora
        if self.is_failure:
            return None

        value = self.as_exception if self.is_exception else self.as_result
        if value is None:
            return None

        vector_extractor = [None]
        def transform_to_json():
            assert vector_extractor[0] is not None
            transformer = PyforaToJsonTransformer(max_byte_count)
            result = None
            try:
                res = self.object_converter.transformPyforaImplval(
                    value,
                    transformer,
                    vector_extractor[0])

                if transformer.anyListsThatNeedLoading:
                    return None

                result = {
                    'result': res,
                    'isException': self.is_exception
                    }

                if self.is_exception:
                    result['trace'] = self.exception_code_locations_as_json()

            except pyfora.ForaToPythonConversionError as e:
                if self.is_exception:
                    result = {
                        'result': {
                            "untranslatableException": str(ForaValue.FORAValue(value))
                            },
                        'isException': True,
                        'trace': self.exception_code_locations_as_json()
                        }
                else:
                    result = {
                        'foraToPythonConversionError': e.message
                        }
            self.result = result
            return self.result

        vector_extractor[0] = self.cache_loader.get_vector_extractor(value, transform_to_json)
        as_json = transform_to_json()
        return as_json


    @property
    def args(self):
        return self._state.args


    @property
    def cumulus_id(self):
        return self._state.cumulus_id


    @property
    def is_completed(self):
        return self._state.result is not None


    @property
    def is_failure(self):
        if self._state.result is None:
            return None
        return self._state.result.isFailure()


    @property
    def is_exception(self):
        return self._state.result.isException()


    @property
    def as_exception(self):
        exception = self._state.result.asException.exception
        if exception is not None and exception.isTuple():
            exception = exception[0]
        return exception


    @property
    def as_result(self):
        return self._state.result.asResult.result


    @property
    def ivc(self):
        return self._state.result


    def exception_code_locations_as_json(self):
        assert self.is_exception
        exception = self._state.result.asException.exception
        if not exception.isTuple():
            return None

        tup = exception.getTuple()
        if len(tup) != 2:
            return None

        _, stacktraceAndVarsInScope = tup
        hashes = stacktraceAndVarsInScope[0].getStackTrace()

        if hashes is None:
            return None

        codeLocations = [ForaNative.getCodeLocation(h) for h in hashes]

        def formatCodeLocation(c):
            if c is None:
                return None
            if not c.defPoint.isExternal():
                return None
            def posToJson(simpleParsePosition):
                return {
                    'characterOffset': simpleParsePosition.rawOffset,
                    'line': simpleParsePosition.line,
                    'col': simpleParsePosition.col
                    }
            return {
                'path': list(c.defPoint.asExternal.paths),
                'range': {
                    'start': posToJson(c.range.start),
                    'stop': posToJson(c.range.stop)
                    }
                }

        # return [x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None]
        return [x for x in [formatCodeLocation(c) for c in codeLocations if c is not None]
                if x is not None]


    def on_computation_result(self, future):
        result, stats = future.result()
        self.set_computation_result(result)
        self.stats = stats


    def set_computation_result(self, result):
        self._state.result = result
        self.computation_status = self.status_from_result(result)


    def status_from_result(self, result):
        if not self.is_completed:
            return None

        if self.is_failure:
            return self.failure_to_json(result.asFailure.error)

        return {
            'status': 'exception' if self.is_exception else 'result'
            }


    @staticmethod
    def failure_to_json(failure):
        message = None

        # Extracts the ErrorState object, defined in ufora/FORA/Core/ErrorState
        if failure.isHalt():
            message = "Computation halted: %s" % failure.asHalt.uuid
        elif failure.isIllegalComputationState():
            message = str(failure.asIllegalComputationState.m0)
        elif failure.isMemoryQuotaExceeded():
            memoryQuotaFailure = failure.asMemoryQuotaExceeded
            message = "Memory quota exceeded (amount: %s, required: %s)" % \
                    (memoryQuotaFailure.amount, memoryQuotaFailure.required)

        return {'status': 'failure', 'message': message}



class RootComputation(Computation):
    def __init__(self, id, cumulus_env, args):
        super(RootComputation, self).__init__(id, cumulus_env, args)
        if 'arg_ids' in self.args:
            assert 'comp_id' not in self.args
            self._state.computation_definition = self.computations.create_computation_definition(
                self.computations.create_apply_tuple(self.args['arg_ids'])
                )
            self._state.cumulus_id = self.computations.create_computation(
                self._state
                )
        else:
            assert 'comp_id' in self.args


    @ExposedProperty
    def as_tuple(self):
        if not self.is_completed:
            return None

        if self.is_exception:
            return self.request_result(max_byte_count=None)

        tuple_ivc = self.object_converter.converter.unwrapPyforaTupleToTuple(self.as_result)
        assert isinstance(tuple_ivc, tuple)
        tuple_elements = [
            TupleElement(uuid.uuid4().hex,
                         self.cumulus_env,
                         {
                             'parent_id': self.computation_id,
                             'index': ix
                         })
            for ix in xrange(len(tuple_ivc))
            ]
        return {
            'isException': False,
            'tupleOfComputedValues': tuple(e.computation_id for e in tuple_elements)
            }



class TupleElement(Computation):
    def __init__(self, id, cumulus_env, args):
        super(TupleElement, self).__init__(id, cumulus_env, args)
        if 'comp_id' not in args:
            self.parent_comp_id = args['parent_id']
            self.index = args['index']
            parent_state = self.computations.get_computation_state(self.parent_comp_id)
            self._state.computation_definition = self.computations.create_computation_definition((
                parent_state.computation_definition,
                ForaNative.makeSymbol("RawGetItemByInt"),
                ForaNative.ImplValContainer(self.index)
                ))
            self._state.cumulus_id = self.computations.create_computation(
                self._state
                )
