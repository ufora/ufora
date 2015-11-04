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

usage_message="$(basename "$0") (worker -m <manager_address> | manager) -d <target_dir> -u <ufora_package> [-s]

Options:
    -d <target_dir>       the root directory under which everything is installed.
    -u <ufora_package>    path to a tarball containing a ufora distribution.
    -m <manager_address>  IP address or hostname of the cluster manager. Only used with 'worker' command.

    -s                    call fakechroot with --use-system-libs
"
usage() { echo "Usage:"; echo "    $usage_message" 1>&2; exit 1; }


# include common functions
SCRIPT_DIR=$(cd $(dirname "$0"); pwd)
. $SCRIPT_DIR/_util.sh

role=
if [ "$1" == "worker" ] || [ "$1" == "manager" ]; then
    role=$1
    shift  # parse the remaining arguments using getopts
else
    echo "ERROR: invalid role '$1'. Must be 'worker' or 'manager'"
    usage
fi

target_dir=
use_sys_libs=
ufora_package=
manager_address=
while getopts "d:u:m:s" o; do
    case $o in
        d)
            target_dir=${OPTARG%%/}
            if [ ! -d "$target_dir" ]; then
                echo "ERROR: Target directory '$target_dir' does not exist."
                usage
            fi
            ;;

        u)
            ufora_package=$OPTARG
            if [ ! -f "$ufora_package" ]; then
                echo "ERROR: Ufora package '$ufora_package' does not exist."
                usage
            fi
            ;;

        m)
            manager_address=$OPTARG
            ;;

        s)
            use_sys_libs="--use-system-libs"
            ;;

        *)
            usage
            ;;
    esac
done

if [ -z "$target_dir" ] || [ -z "$ufora_package" ] || [ -z "$manager_address" -a $role == "worker" ]; then
    echo "ERROR: missing required argument(s)"
    echo ""
    usage
fi

ensure_fakechroot
ensure_fakeroot

chrootdir=`readlink -f $target_dir/image`
install_script=$chrootdir/root/install-ufora-$role.sh

ufora_package_filename=`basename $ufora_package`
# ufora package names are of the form ufora-<version>.<platform>.tar.gz
# we use `basename` to strip the ".tar.gz" suffix and then use ${x%.*} to strip everything from
# the last '.'
# This leaves us with just ufora-<version> and that's the directory name that the package 
# expands to.
ufora_release_name=`basename $ufora_package_filename .tar.gz`
ufora_version=${ufora_release_name%.*}

function write_install_script {
    mkdir -p $chrootdir/root/ufora
    cp $ufora_package $chrootdir/root/ufora


    echo "cd \$HOME/ufora" > $install_script
    echo "tar xvfz $ufora_package_filename" >> $install_script
    echo "cd $ufora_version" >> $install_script

    if [ "$role" == "manager" ]; then
        # update redis.conf to keep data files in /root/ufora/redis/
        echo "mkdir -p /root/ufora/redis/" >> $install_script
        echo "sed -i -s 's@^dir .*@dir /root/ufora/redis/@g' ~/redis-2.8.7/redis.conf" >> $install_script
        echo "~/redis-2.8.7/src/redis-server ~/redis-2.8.7/redis.conf &" >> $install_script
        echo "./install-manager.sh -d \$HOME/ufora" >> $install_script
    else
        echo "./install-worker.sh -d \$HOME/ufora -c $manager_address" >> $install_script
    fi

    chmod u+x $install_script
}

function write_start_script {
    start_script=$chrootdir/root/start-ufora.sh
    cat > $start_script << EOF
cd ~/ufora
if [ "$role" == "manager" ]; then
    # Ensure redis is running
    if [ -z "\`ps aux | grep '[r]edis'\`" ]; then
        ~/redis-2.8.7/src/redis-server ~/redis-2.8.7/redis.conf &
    else
        echo "Redis server already running."
    fi

    echo "Starting ufora cluster manager"
    LD_PRELOAD="\$LD_PRELOAD <IMAGE_ROOT>/usr/local/lib/libtcmalloc.so" bin/start
else
    echo "Starting ufora worker"
    bin/ufora-worker start
fi

# open a new shell to stay inside the chroot after starting ufora
/bin/bash
EOF

    chmod u+x $start_script
}

function write_stop_script {
    stop_script=$chrootdir/root/stop-ufora.sh
    cat > $stop_script << EOF
cd ~/ufora
if [ "$role" == "manager" ]; then
    echo "Stopping ufora cluster manager"
    bin/stop
else
    echo "Stopping ufora worker"
    bin/ufora-worker stop
fi
EOF

    chmod u+x $stop_script
}

write_install_script
$fakeroot $fakechroot $use_sys_libs /usr/sbin/chroot $chrootdir /bin/bash -i /root/`basename $install_script`

write_start_script
write_stop_script

