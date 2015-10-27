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


class TargetCluster(object):
    def __init__(self, clusterName):
        self.clusterName = clusterName
        assert self.clusterName is not None, "target cluster is not set. Use --target=<targetname>"
        if clusterName != 'sim':
            import deploy.stamper.OutputUtils as OutputUtils
            self.clusterInfoDict = OutputUtils.fetchJsonOutputFromCloudformation(clusterName)
        else:
            self.clusterInfoDict = {
                    "ec2_loop_manager_address" : "localhost",
                    "relay_hostname" : "localhost",
                    "cluster_manager_endpoint" : "localhost",
                    "relay_https_port" : "30005",
                    "cluster_type" : "local",
                    "data_bucket" : "bsa.user-data",
                    "logs_bucket" : "ufora.logs"
                }

    def awsCredentials(self):
        dct = self.getClusterInfoDict()
        return dct['worker_aws_key'], dct['worker_aws_secret']

    def dataBucket(self):
        return self.getClusterInfoDict()['data_bucket']

    def logsBucket(self):
        return self.getClusterInfoDict()['logs_bucket']

    def sourceBucket(self):
        return self.getClusterInfoDict()['source_bucket']

    def relayPort(self):
        return self.getClusterInfoDict()['relay_https_port']

    def relayDomain(self):
        return self.getClusterInfoDict()['relay_hostname']

    def getClusterInfoDict(self):
        return self.clusterInfoDict




