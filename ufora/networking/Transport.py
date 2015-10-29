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

class Transport(object):
    def connect(self, credentials):
        """
        Establish a connection on behalf of a user.

        - credentials: a tuple of the form (username, password)
        Returns: a Deferred that fires when the connection attempt completes.
        """
        raise NotImplementedError()

    def send(self, content):
        """
        Send a string of data
        """
        raise NotImplementedError()

    def disconnect(self):
        """
        Close all connections and free any bound resources
        """
        raise NotImplementedError()


