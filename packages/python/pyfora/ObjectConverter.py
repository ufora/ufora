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
import pyfora.Exceptions as Exceptions
import pyfora.TypeDescription as TypeDescription

class ObjectConverter(object):
    def __init__(self, webObjectFactory, purePythonMDSAsJson):
        self.webObjectFactory = webObjectFactory
        self.remoteConverter = webObjectFactory.PyforaObjectConverter()

        def onSuccess(x):
            pass
        def onFailure(x):
            logging.error("ObjectConverter failed to initialize: %s", x)

        self.remoteConverter.initialize({'purePythonMDSAsJson': purePythonMDSAsJson}, {'onSuccess':onSuccess, 'onFailure':onFailure})

    def convert(self, objectId, objectRegistry, callback):
        dependencyGraph = objectRegistry.computeDependencyGraph(objectId)
        objectIdToObjectDefinition = {
            objId: TypeDescription.serialize(objectRegistry.getDefinition(objId))
            for objId in dependencyGraph.iterkeys()
            }

        def onSuccess(message):
            if 'isException' not in message:
                callback(objectId)
            else:
                callback(Exceptions.PythonToForaConversionError(str(message['message']), message['trace']))

        self.remoteConverter.convert(
            {
                'objectId': objectId,
                'objectIdToObjectDefinition': objectIdToObjectDefinition
            },
            {
                'onSuccess': onSuccess,
                'onFailure': lambda err: callback(Exceptions.PythonToForaConversionError(err))
            })



