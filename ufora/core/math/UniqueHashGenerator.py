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

import uuid
import threading
import ufora.native.Hash as Hash
import logging

class UniqueHashGenerator(object):
    """UniqueHashGenerator

    Generates a string of random SHA hashes seeded using a draw from uuid. This class is 
    thread-safe. Hashes pulled from any instance of a UniqueHashGeneratr should be unique
    across the system, assuming that uuid.uuid4 is unique.

    Usage:

        x = UniqueHashGenerator()

        hash1 = x()
        hash2 = x()
        ...

    """
    def __init__(self):
        self.seed_ = None
        self.lock_ = threading.Lock()

    def __call__(self):
        with self.lock_:
            if self.seed_ is None:
                self.seed_ = Hash.Hash.sha1(str(uuid.uuid4()))
            self.seed_ = self.seed_ + self.seed_
            return self.seed_

