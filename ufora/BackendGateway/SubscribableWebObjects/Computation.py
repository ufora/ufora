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

from ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaToJsonTransformer \
    import PyforaToJsonTransformer
from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedFunction, ExposedProperty, observable
import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.FORA as ForaNative


class Computation(SubscribableObject):
    def __init__(self, id, cumulus_env, args):
        super(Computation, self).__init__(id, cumulus_env)
        self.arg_ids = args['arg_ids']
        self.computation_definition = self.computations.create_computation_definition(
            self.computations.create_apply_tuple(self.arg_ids)
            )
        self._computation_id = self.computations.create_computation(self.computation_definition)

        self._result = None
        self._status = None
        self._stats = None
        self._json_result = None


    @ExposedFunction
    def start(self, _):
        logging.info("starting computation")
        future = self.computations.start_computation(self._computation_id)
        logging.info("computation started")
        future.add_done_callback(self.on_computation_result)
        return True


    @ExposedProperty
    def computation_id(self):
        comp_id = self._computation_id.toSimple()
        logging.info("computation_id: %s", comp_id)
        return comp_id


    @ExposedProperty
    def computation_status(self):
        return self._status


    @computation_status.setter
    @observable
    def computation_status(self, value):
        self._status = value


    def set_computation_result(self, result):
        self._result = result
        self.computation_status = self.status_from_result(result)


    @ExposedProperty
    def stats(self):
        return self._stats


    @stats.setter
    @observable
    def stats(self, value):
        self._stats = value


    @ExposedProperty
    def result(self):
        return self._json_result


    @result.setter
    @observable
    def result(self, value):
        self._json_result = value


    @ExposedFunction
    def request_result(self, max_byte_count):
        import pyfora
        if self.is_failure:
            return None

        value = self.as_exception if self.is_exception else self.as_result
        if value is None:
            return None

        def transform_to_json(vector_extractor):
            transformer = PyforaToJsonTransformer(max_byte_count)
            result = None
            try:
                res = self.object_converter.transformPyforaImplval(
                    value,
                    transformer,
                    vector_extractor)

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

        vector_extractor = self.cache_loader.get_vector_extractor(value, transform_to_json)
        as_json = transform_to_json(vector_extractor)
        logging.info("result as json: %s", as_json)
        return as_json


    def exception_code_locations_as_json(self):
        assert self.is_exception
        exception = self._result.asException.exception
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
        logging.info("computation result: %s", result)
        self.set_computation_result(result)
        self.stats = stats


    @property
    def is_completed(self):
        return self._result is not None


    @property
    def is_failure(self):
        if self._result is None:
            return None
        return self._result.isFailure()


    @property
    def is_exception(self):
        return self._result.isException()


    @property
    def as_exception(self):
        exception = self._result.asException.exception
        if exception is not None and exception.isTuple():
            exception = exception[0]
        return exception


    @property
    def as_result(self):
        return self._result.asResult.result


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
