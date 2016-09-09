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

# Start Ufora in local fakechroot environment

# First read the original package build path from ./local/build_path
# (relative to the script's directory) and substitute it with the absolute path
# to ./local/build_path, in all configuration files under ./local
root_path=$(readlink -e $(dirname "$0"))
local_path=$root_path/local
image_path=$root_path/image
pushd $local_path
build_path=`cat ../build_path`

if [ ! -z "$(grep -rIl $build_path *)" ]; then
    echo "Replacing original build path $build_path with new path $local_path."
    grep -rIl $build_path * | xargs sed -i s^$build_path^$local_path^g
fi


if [ ! -z "$(grep -l "<IMAGE_ROOT>" $root_path/image/root/start-ufora.sh)" ]; then
    sed -i -s "s^<IMAGE_ROOT>^$image_path^g" $root_path/image/root/start-ufora.sh
fi

fakeroot=$local_path/bin/fakeroot
fakechroot=$local_path/bin/fakechroot
chrootdir=$root_path/image
$fakeroot $fakechroot /usr/sbin/chroot $chrootdir /bin/bash -i /root/start-ufora.sh
