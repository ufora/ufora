#!/bin/sh

REPO_ROOT=$(cd $(dirname "$0")/../../..; pwd)

usage() { echo "Usage: $0 -v <version> -d <dest_dir>" 1>&2; exit 1; }

while getopts "v:d:p:" o; do
  case "${o}" in
    v)
      v=${OPTARG}
      ;;
    d)
      d=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done

shift $((OPTIND-1))

if [ -z "${v}" ] || [ -z "${d}" ] ; then
    usage
fi

if [ ! -d "${d}" ] ; then
    echo "Error: Target directory ${d} does not exist"
    usage
fi

TARGET="${d}/ufora-${v}.tar.gz"
if [ -f "$TARGET" ]; then
    echo "Error: Destination file $TARGET already exists."
    usage
fi

echo "Packaging ufora version ${v} into ${TARGET}"

cd $REPO_ROOT/ufora/web/relay
rm -rf node_modules/ > /dev/null

npm install
if [ $? -ne 0 ]; then
  echo "Error: 'npm install' exited with non-zero code."
  exit 2
fi

cd $REPO_ROOT
DEST_DIR=${d}/ufora-${v}
rm -rf $DEST_DIR
mkdir -p $DEST_DIR
echo "Copying ufora source code"
rsync -a --exclude '*.cppml' --exclude '*.cpp' --exclude '*.hppml' --exclude '*.hpp' --exclude '*.pyc' $REPO_ROOT/ufora $DEST_DIR/lib
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
rsync -a $REPO_ROOT/license/ $DEST_DIR/license
cp $REPO_ROOT/docker/service/Dockerfile $DEST_DIR

cd ${d}
tar cfz $TARGET ufora-${v}
rm -rf $DEST_DIR
echo "Packaging complete"
