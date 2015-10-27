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

import os


def is_enabled():
    return os.getenv("BSA_PYCOVERAGE", '0') == '1'


def start_collection():
    import coverage
    cov = coverage.coverage(data_suffix=True)
    cov.start()
    return cov


def stop_collection(cov):
    cov.save()
    cov.stop()


def adjusted_timeout(timeout):
    return timeout * 4 if is_enabled() else timeout

