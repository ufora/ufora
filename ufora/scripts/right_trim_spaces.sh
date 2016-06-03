#!/bin/bash
# This script removes all trailing whitespace from files with specific 
# extensions under a specified root directory.
EXTENSIONS="hppml  cppml  hpp  cpp  py"
ROOT_DIR="../../ufora"

for ext in ${EXTENSIONS}; do
  echo "Right trim whitespace for extension '*.${ext}'"
  find ${ROOT_DIR} -type f -name "*.${ext}" -exec sed --in-place 's/[[:space:]]\+$//' {} \+
done
