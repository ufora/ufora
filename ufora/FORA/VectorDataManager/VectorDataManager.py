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

import ufora.config.Setup as Setup
import ufora.native.FORA as FORANative
import logging

def constructVDM(
        callbackScheduler,
        vectorRamCacheBytes = None,
        maxRamCacheBytes = None,
        maxVectorChunkSize = None
        ):
    if vectorRamCacheBytes is None:
        vectorRamCacheBytes = Setup.config().cumulusVectorRamCacheMB * 1024 * 1024

    if maxRamCacheBytes is None:
        maxRamCacheBytes = Setup.config().cumulusMaxRamCacheMB * 1024 * 1024

    if maxVectorChunkSize is None:
        maxVectorChunkSize = Setup.config().maxPageSizeInBytes

        if maxVectorChunkSize > vectorRamCacheBytes / 32:
            logging.info(
                "VDM constructor specified a chunk size of %s MB " +
                "and a memory size of %s MB. Reducing the chunk size because its too large",
                vectorRamCacheBytes / 1024.0 / 1024.0,
                maxVectorChunkSize / 1024.0 / 1024.0
                )

            maxVectorChunkSize = vectorRamCacheBytes / 32

    logging.info("Creating a VDM with %s MB of memory and %s max vector size",
        vectorRamCacheBytes / 1024.0 / 1024.0,
        maxVectorChunkSize / 1024.0 / 1024.0
        )

    VDM = FORANative.VectorDataManager(callbackScheduler, maxVectorChunkSize)
    VDM.setMemoryLimit(vectorRamCacheBytes, maxRamCacheBytes)

    return VDM

