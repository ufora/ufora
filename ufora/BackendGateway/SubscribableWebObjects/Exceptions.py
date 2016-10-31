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

import logging
import traceback
import uuid

class SubscribableWebObjectsException(Exception):
    pass

def wrapException(inException):
    """Turn an exception into a SubscribableWebObjectsException and log its data with a guid.

    If the exception is already a SubscribableWebObjectsException, just return it unmodified.
    """
    if isinstance(inException, SubscribableWebObjectsException):
        return inException

    guid = str(uuid.uuid4())

    logging.error(
        "Invalid user exception encountered: GUID = %s\n%s\n%s",
        guid,
        inException.message,
        traceback.format_exc()
        )

    return SubscribableWebObjectsException("Unknown exception. Guid = %s" % guid)

class InvalidFieldAssignment(SubscribableWebObjectsException):
    def __init__(self, what):
        SubscribableWebObjectsException.__init__(self, what)

class InternalError(SubscribableWebObjectsException):
    def __init__(self, what):
        SubscribableWebObjectsException.__init__(self, what)

class ComputeError(SubscribableWebObjectsException):
    def __init__(self, what):
        SubscribableWebObjectsException.__init__(self, what)

class AuthorizationError(SubscribableWebObjectsException):
    def __init__(self, what):
        SubscribableWebObjectsException.__init__(self, what)

