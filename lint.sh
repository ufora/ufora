#!/bin/bash
pushd `dirname $0`

echo "Compiling python..."
python -m compileall -q "*" || exit $?

echo "Running pylint..."
pylint --rcfile "./.pylint.rc" `find ufora test_scripts -type f -iname "*.py" -not -iname "Qt*.py"` || exit $?

echo "Done!"
