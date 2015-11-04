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

# Builds and packages Ufora
###########################
#
# Parameters:
#   clean - clean all prior build artifacts
#   build - configure and build ufora binaries
#   package - build a ufora distribution package
#
#   If no parameter is specified, the script runs all commands.
#
# Environment Variables:
#   BUILD_COMMIT - The full git commitish of the commit being built.
#                  Used to name the distribution packagee.
#                  Only required with the 'package' command.
#   OUTPUT_DIR -   Directory in which the built distribution package is created.
#                  Only required with the 'package' command.
#   CCACHE_DIR -   [optional] Location of ccache directory
##########################################################

dockerfile_hash=`md5sum docker/build/Dockerfile`
if [ $? -ne 0 ]; then
    echo "Unable to hash Dockerfile. Aborting."
    exit 1
fi
dockerfile_hash=`echo $dockerfile_hash | awk '{print $1}'`

docker_image="ufora/build:$dockerfile_hash"
docker pull $docker_image
if [ $? -ne 0 ]; then
    echo "Failed to pull docker image $docker_image. Building new image."
    docker build -t $docker_image docker/build
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to build docker image. Exiting."
        exit 1
    fi
    docker push $docker_image
fi

clean_command="rm -rf .waf-*-* ; ./waf clean > /dev/null ; rm -rf .build > /dev/null"
reset_axioms_command="PYTHONPATH=/volumes/src ufora/scripts/resetAxiomSearchFunction.py"
rebuild_axioms_command="PYTHONPATH=/volumes/src ufora/scripts/rebuildAxiomSearchFunction.py"
configure_command="CC=clang-3.5 CXX=clang++-3.5 ./waf configure"
build_once_command="CC=clang-3.5 CXX=clang++-3.5 ./waf install"

build_command="$reset_axioms_command; $configure_command; $build_once_command; $rebuild_axioms_command; $build_once_command"

package_command="PYTHONPATH=/volumes/src ufora/scripts/package/create-package.sh -d /volumes/output -v $BUILD_COMMIT"

command_to_run=""
while (( "$#" )); do
    if [[ "$1" == "clean" ]]; then
        if [[ -z "$command_to_run" ]]; then
            command_to_run=$clean_command
        else
            command_to_run="$command_to_run ; $clean_command"
        fi
    elif [[ "$1" == "build" ]]; then
        if [[ -z "$command_to_run" ]]; then
            command_to_run=$build_command
        else
            command_to_run="$command_to_run ; $build_command"
        fi
    elif [[ "$1" == "package" ]]; then
        if [[ -z "$command_to_run" ]]; then
            command_to_run=$package_command
        else
            command_to_run="$command_to_run ; $package_command"
        fi
    elif [[ "$1" == "test" ]]; then
        shift
        if [[ -z "$command_to_run" ]]; then
            command_to_run=$*
        else
            command_to_run="$command_to_run ; $*"
        fi
        break
    else
        echo "ERROR: Invalid command '$1'."
        exit 1
    fi
    shift
done

if [[ -z "$command_to_run" ]]; then
    echo "Running default command - clean, build and package"
    command_to_run="$clean_command ; $build_command && $package_command"
fi

echo "Running command: $command_to_run"

repo_dir=$(cd $(dirname "$0"); pwd) # make.sh is at the root of the repo
echo "OUTPUT_DIR: $OUTPUT_DIR"

src_volume="-v $repo_dir:/volumes/src"
if [ ! -z $OUTPUT_DIR ]; then
    output_volume="-v $OUTPUT_DIR:/volumes/output"
fi
if [ ! -z $CCACHE_DIR ]; then
    ccache_volume="-v $CCACHE_DIR:/volumes/ccache"
fi


container_env="-e UFORA_PERFORMANCE_TEST_RESULTS_FILE=$UFORA_PERFORMANCE_TEST_RESULTS_FILE \
               -e AWS_AVAILABILITY_ZONE=$AWS_AVAILABILITY_ZONE \
               -e TEST_LOOPER_TEST_ID=$TEST_LOOPER_TEST_ID \
               -e TEST_LOOPER_MULTIBOX_IP_LIST=${TEST_LOOPER_MULTIBOX_IP_LIST// /,} \
               -e TEST_LOOPER_MULTIBOX_OWN_IP=$TEST_LOOPER_MULTIBOX_OWN_IP \
               -e TEST_OUTPUT_DIR=/volumes/output \
               -e REVISION=$REVISION"


container_name=`uuidgen`

if [ ! -z "$TEST_LOOPER_MULTIBOX_IP_LIST" ]; then
    network_settings="--net=host"
fi

function cleanup {
    docker stop $container_name &> /dev/null
    docker rm $container_name &> /dev/null
}

# Ensure the container is not left running
trap cleanup EXIT

docker run --rm --name $container_name \
    $container_env \
    $network_settings \
    $src_volume \
    $output_volume \
    $ccache_volume \
    $docker_image bash -c "cd /volumes/src; $command_to_run"
