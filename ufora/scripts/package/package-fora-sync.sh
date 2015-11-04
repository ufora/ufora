#!/bin/bash

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

usage_message="$(basename "$0") -d <target_dir> -v <version>

Options:
    -d <target_dir>       directory where target package is created
    -v <version>          package version number
"
usage() { echo "Usage:"; echo "    $usage_message" 1>&2; exit 1; }

target_dir=
version=
while getopts "v:d:" o; do
  case "${o}" in
    v)
      version=$OPTARG
      ;;
    d)
      target_dir=$OPTARG
      ;;
    *)
      usage
      ;;
  esac
done


if [ -z "$target_dir" ] || [ -z "$version" ]; then
    echo "ERROR: missing required argument(s)"
    echo ""
    usage
fi

if [ ! -d "$target_dir" ]; then
  mkdir -p $target_dir
  if [ $? -ne 0 ]; then
    echo "ERROR: Unable to create target directory: $target_dir."
    exit 1
  fi
fi

if [ "`uname -s`" == "Darwin" ]; then
  tmpdir=`mktemp -d -t fora-sync`
else
  tmpdir=`mktemp -d`
fi
packagename="fora-sync-$version"
packageroot="$tmpdir/$packagename"
mkdir $packageroot
echo "Packaging in $packageroot"

cat >> $tmpdir/filelist << EOF
ufora/scripts/package/fora-sync/install.sh /
ufora/scripts/package/fora-sync/README.md /
ufora/scripts/package/fora-sync/INSTALL.md /
ufora/scripts/fora-sync /bin
ufora/scripts/ProjectStoreConnection.coffee /bin
ufora/scripts/readProjectFromSharedState.py /bin
ufora/scripts/writeProjectToSharedState.py /bin
ufora/web/relay/tsunami/coffee/SocketIoJsonInterface.coffee /web/relay/tsunami/coffee
ufora/web/relay/tsunami/coffee/SubscribableWebObjects.coffee /web/relay/tsunami/coffee
ufora/web/relay/tsunami/coffee/logging.coffee /web/relay/tsunami/coffee
ufora/__init__.py /ufora
ufora/BackendGateway/__init__.py /ufora/BackendGateway
ufora/BackendGateway/ProjectReaderWriter.py /ufora/BackendGateway
ufora/BackendGateway/BackendGatewayTransport.py /ufora/BackendGateway
ufora/FORA/__init__.py /ufora/FORA
ufora/FORA/python/__init__.py /ufora/FORA/python
ufora/FORA/python/ModuleDirectoryStructure.py /ufora/FORA/python
ufora/util/__init__.py /ufora/util
ufora/util/TypeAwareComparison.py /ufora/util
EOF

cat >> $packageroot/package.json << EOF
{
  "name": "fora-sync",
  "version": "0.7.7",
  "dependencies": {
    "argparse": " 0.1.x",
    "async": " 0.1.x",
    "socket.io": "0.9.x",
    "underscore": "~1.5.2",
    "read": "~1.0.5"
  },
  "engines": {
    "node": "0.8.x"
  }
}
EOF

while IFS=' ' read source dest
do
  dest=$packageroot$dest
  echo "copying $source to $dest"
  if [ ! -d "$dest" ]; then
    mkdir -p $dest
  fi

  cp -r $source $dest
done < $tmpdir/filelist

cd $tmpdir
tar cvfz $target_dir/$packagename.tar.gz $packagename

