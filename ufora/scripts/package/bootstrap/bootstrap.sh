#!/bin/bash

# sudo apt-get install -y debootstrap git libcap-dev dh-autoreconf

usage_message="$(basename "$0") -r <precise|wheezy> -d <target_dir> [-s]

Options:
    -r <precise|wheezy>   the Debian/Ubuntu release to use for bootstraping. Can be one of 'precise, wheezy'.
    -d <target_dir>       the root directory under which everything is installed.

    -s                    call fakechroot with --use-system-libs
"
usage() { echo "Usage:"; echo "    $usage_message" 1>&2; exit 1; }


# include common functions
SELF_DIR=$(cd $(dirname "$0"); pwd)
. $SELF_DIR/_util.sh

function check_prereqs {
    debootstrap="/usr/sbin/debootstrap"
    if [ ! -f "$debootstrap" ]; then
        echo "Error: Cannot bootstrap package because 'debootstrap' is not installed. Run 'apt-get install debootstrap' to install it."
        exit 1
    fi
}

check_prereqs

release=
target_dir=
use_sys_libs=
while getopts "r:d:s" o; do
    case $o in
        r)
            release=$OPTARG
            if [ "$release" != "precise" -a "$release" != "wheezy" ]; then
                echo "ERROR: Invalid release name '$release'"
                echo .
                usage
            fi
            ;;

        d)
            target_dir=${OPTARG%%/}
            if [ ! -d "$target_dir" ]; then
                echo "ERROR: Target directory '$target_dir' does not exist."
                usage
            fi
            ;;

        s)
            use_sys_libs="--use-system-libs"
            ;;

        *)
            usage
            ;;
    esac
done

if [ -z "$release" ] || [ -z "$target_dir" ]; then
    echo "ERROR: missing required argument(s)"
    echo ""
    usage
fi

ensure_fakechroot
ensure_fakeroot


chrootdir=$target_dir/image

function bootstrap_target {
    if [ -d "$chrootdir" ] && [ "`ls -1 $chrootdir`" != "" ]; then
        echo "ERROR: target directory exists and is not empty. Aborting."
        exit 1
    else
        mkdir -p $chrootdir
    fi

    $fakeroot $fakechroot $use_sys_libs debootstrap --variant=fakechroot $release $chrootdir
}

function update_bashrc {
    sed -i.bak -n '/### UFORA ###/q' $chrootdir/etc/bash.bashrc
    cat >> $chrootdir/etc/bash.bashrc << EOF
### UFORA ###
#############
export HOME=/root
cd ~

if [ ! -f ~/.nvm/nvm.sh ]; then
    echo "ERROR: Required dependency Node Version Manager (nvm) is not installed."
    echo "       You will not be able to run the Ufora cluster manager in this environment."
fi

if [ -f ~/.nvm/nvm.sh ]; then
    . ~/.nvm/nvm.sh
    if [ -z "\`nvm ls | grep v0.10.28 | head -1\`" ]; then
        echo "ERROR: node.js version 0.10.28 should be installed but is not available."
        echo "       You will not be able to run the Ufora cluster manager in this environment."
    else
        nvm use v0.10.28
    fi
fi
EOF
}

function write_install_script {
    if [ "$release" == "precise" ]; then
        echo "deb http://archive.ubuntu.com/ubuntu precise main restricted universe multiverse" > $chrootdir/etc/apt/sources.list
    fi

    cat > $chrootdir/root/install_dependencies.sh << EOF
export HOME=/root
cd ~
if [ "\$(pwd)" != "/root" ]; then
    echo "BAD home directory!"
    exit 1
fi

apt-get update
apt-get install -y curl wget git make gcc g++ python python-pip python-dev libblas3gf liblapack3gf unixodbc-dev libffi-dev libunwind7-dev tcl8.5

# The libraries below are installed into subdirectories of /usr/lib. A config file is required
# for the dynamic loader (ld) to be able to find them.
echo /usr/lib/libblas > /etc/ld.so.conf.d/libblas.conf
echo /usr/lib/lapack > /etc/ld.so.conf.d/lapack.conf

pip install nose twisted pyOpenSSL service_identity requests pyodbc redis numpy boto markdown bcrypt selenium

# Install NVM (nodejs package manager)
curl https://raw.githubusercontent.com/creationix/nvm/v0.8.0/install.sh | sh
. ~/.nvm/nvm.sh
nvm install v0.10.28
nvm use v0.10.28
npm install -g forever coffee-script mocha

cd ~
wget https://gperftools.googlecode.com/files/gperftools-2.1.tar.gz
tar xvfz gperftools-2.1.tar.gz
cd gperftools-2.1
./configure && make && make install
if [ \$? -ne 0 ]; then
    echo "Error: Failed to build gperftools."
    exit 2
fi
rm gperftools-2.1.tar.gz

cd ~
wget http://download.redis.io/releases/redis-2.8.7.tar.gz
tar xvfz redis-2.8.7.tar.gz
cd redis-2.8.7
make && make install && make test
if [ \$? -ne 0 ]; then
    echo "Error: Failed to build redis."
    exit 2
fi
rm ../redis-2.8.7.tar.gz
EOF

    chmod +x $chrootdir/root/install_dependencies.sh
}


function write_start_stop_scripts {
    cp $SELF_DIR/scripts/start.sh $target_dir/start.sh
    chmod +x $target_dir/start.sh

    cp $SELF_DIR/scripts/stop.sh $target_dir/stop.sh
    chmod +x $target_dir/stop.sh

    cp $SELF_DIR/scripts/configure_worker.sh $target_dir/configure_worker.sh
    chmod +x $target_dir/configure_worker.sh
}


bootstrap_target
write_install_script
$fakeroot $fakechroot $use_sys_libs /usr/sbin/chroot $chrootdir /bin/bash -i /root/install_dependencies.sh
update_bashrc
write_start_stop_scripts

