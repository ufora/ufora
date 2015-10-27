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
import ufora.config.TargetCluster as TargetCluster

class LoginConfiguration:
    """LoginConfiguration

    Represents credentials and a target necessary to connect to some kind of remote server.
    """

    def __init__(self, username, password, isInMemory, targetClusterInfoDict):
        self.username = username
        self.password = password
        self.isInMemoryCluster = isInMemory
        self.targetClusterInfoDict = targetClusterInfoDict

    @staticmethod
    def defaultForTesting():
        return LoginConfiguration("test", "asdfasdf", True, {})

    @staticmethod
    def defaultForSimulation(config):
        return LoginConfiguration(
                    "test",
                    "asdfasdf",
                    False,
                    LoginConfiguration.getClusterInfo('sim', config)
                    )

    @staticmethod
    def fromParsedArguments(parsedArgs, currentConfig):
        clusterInfoDict = {}
        isInMemory = False
        if 'cluster' in parsedArgs and parsedArgs.cluster is not None:
            host, port =  LoginConfiguration.parseCluster(parsedArgs.cluster)
            clusterInfoDict = {
                                'relay_hostname': host,
                                'relay_https_port': port,
                                'relay_tcp_port': 30007
                              }
        elif 'target' in parsedArgs and parsedArgs.target is not None:
            if parsedArgs.target == "inMemory":
                isInMemory = True
            else:
                clusterInfoDict = LoginConfiguration.getClusterInfo(parsedArgs.target, currentConfig)
        else:
            return None

        username = LoginConfiguration.readOptionalArgument(parsedArgs.user, 'FORA_USER', None)
        password = LoginConfiguration.readOptionalArgument(parsedArgs.password, 'FORA_SECRET', None)

        return LoginConfiguration(
            username,
            password,
            isInMemory,
            clusterInfoDict
            )

    @staticmethod
    def readOptionalArgument(arg, envVar, fallback):
        if arg is not None:
            return arg
        if envVar in os.environ:
            return os.environ[envVar]
        return fallback

    @staticmethod
    def parseCluster(clusterString):
        parts = clusterString.split(':')
        assert len(parts) > 0
        port = 443
        if len(parts) > 1:
            port = int(parts[1])
        return (parts[0], port)

    @staticmethod
    def getClusterInfo(target, config):
        return TargetCluster.TargetCluster(target).getClusterInfoDict()

    def getS3Credentials(self):
        return self.targetClusterInfoDict['worker_aws_key'], self.targetClusterInfoDict['worker_aws_secret']


