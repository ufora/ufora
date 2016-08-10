clean_command="rm -rf .waf-*-* ; ./waf clean > /dev/null ; rm -rf .build > /dev/null"
reset_axioms_command="PYTHONPATH=/volumes/src ufora/scripts/resetAxiomSearchFunction.py"
rebuild_axioms_command="PYTHONPATH=/volumes/src ufora/scripts/rebuildAxiomSearchFunction.py"
configure_command="CC=clang-3.5 CXX=clang++-3.5 ./waf configure"
build_once_command="CC=clang-3.5 CXX=clang++-3.5 ./waf install"

build_command="$reset_axioms_command; $configure_command; $build_once_command; $rebuild_axioms_command; $build_once_command"

package_command="PYTHONPATH=/volumes/src ufora/scripts/package/create-package.sh -d /volumes/output -v $BUILD_COMMIT"

command_to_run="$clean_command ; $build_command && $package_command"

echo "Running command: $command_to_run"

cd /volumes/src; 

eval $command_to_run
