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

import ufora.native.SharedState as SharedStateNative
import ufora.config.Setup as Setup
import ufora.config.Mainline as Mainline
import sys
import ufora.native.Json as NativeJson

def sharedStateToHumanReadableFormat(path, outputStream):
    storage = SharedStateNative.Storage.FileStorage(path, 100, 10)
    keyspaces = storage.populatedKeyspaces()

    toWrite = []

    for k in keyspaces:
        storageForKeyspace = storage.storageForKeyspace(k, 0)
        data = storageForKeyspace.readKeyValueMap()
        
        entries = []
        for key,val in data.iteritems():
            entries.append(
                NativeJson.Json(
                    {'key': tuple(key[ix] for ix in range(len(key))), 
                     'val': val
                     }
                    )
                )

        toWrite.append({
            'keyspace': (k.type, k.name, k.dimension),
            'values': entries
            })

    print >> outputStream, NativeJson.Json(toWrite)

def main(parsedArgs):
    sharedStateToHumanReadableFormat(parsedArgs.path, sys.stdout)


if __name__ == "__main__":
    parser = Setup.defaultParser(description="Dump the contents of SharedState to standard out")
    parser.add_argument('path', help='path to the shared-state directory')

    Mainline.UserFacingMainline(main, sys.argv, parser=parser)





