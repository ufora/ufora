#!/bin/sh

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

REPO_ROOT=$(cd $(dirname "$0")/../../..; pwd)

usage() { echo "Usage: $0 -v <version> -d <dest_dir> [-f]" 1>&2; exit 1; }

while getopts "v:d:f" o; do
  case "${o}" in
    v)
      version=${OPTARG}
      ;;
    d)
      d=${OPTARG}
      ;;
    f)
      force=1
      ;;
    *)
      usage
      ;;
  esac
done

shift $((OPTIND-1))

if [ -z $version ] || [ -z $d ] ; then
    usage
fi

if [ ! -d "$d" ] ; then
    echo "Error: Target directory $d does not exist"
    usage
fi

TARGET="$d/ufora-${version}.tar.gz"
if [ -f "$TARGET" ]; then
    if [ $force ]; then
      echo "Deleting existing package: $TARGET"
      rm -f $TARGET
      if [ $? -ne 0 ]; then
        echo "Error: Unable to delete existing package - $TARGET"
        exit 1
      fi
    else
      echo "Error: Destination file $TARGET already exists."
      usage
    fi
fi

echo "Packaging ufora version ${version} into ${TARGET}"

cd $REPO_ROOT/ufora/web/relay
rm -rf node_modules/ > /dev/null

npm install
if [ $? -ne 0 ]; then
  echo "Error: 'npm install' exited with non-zero code."
  exit 2
fi

cd $REPO_ROOT
DEST_DIR=$d/ufora-${version}
rm -rf $DEST_DIR
mkdir -p $DEST_DIR
echo "Copying ufora source code"
rsync -a --exclude '*.cppml' --exclude '*.cpp' --exclude '*.hppml' --exclude '*.hpp' --exclude '*.pyc' --exclude '*.cfg' $REPO_ROOT/ufora $DEST_DIR/lib
if [ $? -ne 0 ]; then
  echo "Error: Failed to rsync /ufora directory"
  exit 2
fi
echo "Copying test scripts"
rsync -a --exclude '*.pyc' $REPO_ROOT/test_scripts $DEST_DIR/lib
if [ $? -ne 0 ]; then
  echo "Error: Failed to rsync /test_scripts directory"
  exit 2
fi
cp $REPO_ROOT/test.py $DEST_DIR/lib
cp $REPO_ROOT/make.sh $DEST_DIR/lib
rsync -a $REPO_ROOT/docker $DEST_DIR/lib
echo "Copying packages"
rsync -a --exclude '*.pyc' --exclude build/ --exclude dist/ --exclude pyfora.egg-info/ $REPO_ROOT/packages $DEST_DIR/lib
if [ $? -ne 0 ]; then
  echo "Error: Failed to rsync /packages directory"
  exit 2
fi
cp $REPO_ROOT/LICENSE $DEST_DIR
rsync -a $REPO_ROOT/licenses/ $DEST_DIR/licenses
cp $REPO_ROOT/docker/service/* $DEST_DIR

cd $d
tar cfz $TARGET ufora-${version}
rm -rf $DEST_DIR
echo "Packaging complete"
