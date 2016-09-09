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

import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.Cumulus as CumulusNative
import ufora.native.Hash as HashNative
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import logging
import traceback

class WriteToS3Task(ComputedGraph.Location):
    #the computation we want to write
    computedValue = object
    bucketname = object
    keyname = object

    #either None if it's uploading, or {'success': True/False, ['message': msg]}
    successOrError = ComputedGraph.Mutable(object, lambda: None, exposeToProtocol=True)

    @ComputedGraph.Function
    def trigger(self):
        if self.successOrError is not None:
            return

        if self.computedValue.valueIVC is None:
            self.successOrError={'success':False, 'message': "Tried to trigger write before calculation was finished."}
            return

        if not self.computedValue.valueIVC.isVectorOfChar():
            self.successOrError={'success':False, 'message': "Result should have been a string."}
            return
        if self.computedValue.isException:
            self.successOrError={'success':False, 'message': "Result should have been a string. Got an exception instead."}
            return

        def callback(result):
            if result.isSuccess():
                self.successOrError={'success':True}
            else:
                self.successOrError={'success':False, 'message': str(result)}

        ComputedValueGateway.getGateway().createExternalIoTask(
            CumulusNative.ExternalIoTask.WriteCharBigvecToS3(
                self.computedValue.valueIVC.getVectorBigvecGuid(),
                CumulusNative.S3KeyAndCredentials(
                    self.bucketname,
                    self.keyname,
                    "",
                    "",
                    ""
                    )
                ),
            callback
            )

