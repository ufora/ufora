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

import zope.interface

class Transport(zope.interface.Interface):
    onMessageReceived = zope.interface.Attribute(
                            """A callback that is fired whenever a message is received.
                               It takes a single string argument that holds the incoming message.
                            """)

    def connect(credentials):
        """
        Establish a connection on behalf of a user.

        - credentials: a tuple of the form (username, password)
        Returns: a Deferred that fires when the connection attempt completes.
        """

    def send(content):
        """
        Send a string of data
        """

    def disconnect():
        """
        Close all connections and free any bound resources
        """


