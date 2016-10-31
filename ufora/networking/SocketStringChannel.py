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

import ufora.native.SocketStringChannel as SocketStringChannelNative

#note that when we create native Channel objects, we need to keep the python object alive
#indefinitely. Otherwise, if we lose the python socket, it will close the file descriptor.
#we can't use os.dup to duplicate the descriptors because it occasionally produces file descriptors
#that conflict with incoming sockets.

allSockets_ = []

def SocketStringChannel(callbackScheduler, socket):
    """Create a SocketStringChannel from a python socket object.
    
    The resulting class is an instance of ufora.native.StringChannel.StringChannel. We keep the 
    python socket object alive. This prevents it from releasing the file descriptor on its own,
    since the SocketStringChannel does that itself.
    """
    allSockets_.append(socket)
    return SocketStringChannelNative.SocketStringChannel(callbackScheduler, socket.fileno())



