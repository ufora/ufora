function has_fakechroot {
    candidate=$target_dir/local/bin/fakechroot
    if [ -f "$candidate" ] && [ "`$candidate --version`" == "fakechroot version 2.17.3" ]; then
        fakechroot=$candidate
    fi
}

function build_fakechroot {
    if [ ! -f "`which git`" ]; then
        echo "Error: cannot clone project because 'git' is not installed. You can install git by running 'apt-get install git'."
        exit 1
    fi
    if [ ! -f "`which autoreconf`" ]; then
        echo "Error: cannot build project because 'autoreconf' is not installed. You can install it by running 'apt-get install dh-autoreconf'."
        exit 1
    fi
    cd $target_dir
    if [ ! -d local ]; then
        mkdir local
    fi
    git clone https://github.com/dex4er/fakechroot.git fakechroot-src
    cd fakechroot-src
    ./autogen.sh
    ./configure --prefix=$target_dir/local
    make -j 8 && make install
    if [ $? - ne 0 ]; then
        echo "ERROR: Failed to build fakechroot."
        exit 2
    fi
    write_build_path
    fakechroot=$target_dir/local/bin/fakechroot
}

function ensure_fakechroot {
    fakechroot=
    has_fakechroot
    if [ -z "$fakechroot" ]; then
        echo "Building fakechroot"
        build_fakechroot
    else
        echo "Using fakechroot from: $fakechroot"
    fi
}

function write_build_path {
    build_path=`readlink -e $target_dir/local`
    echo $build_path > $target_dir/build_path
}

function has_fakeroot {
    candidate=$target_dir/local/bin/fakeroot
    if [ -f "$candidate" ]; then
        fakeroot=$candidate
    fi
}

function build_fakeroot {
    if [ ! -f "`which git`" ]; then
        echo "Error: cannot clone project because 'git' is not installed. You can install git by running 'apt-get install git'."
        exit 1
    fi
    if [ ! -f "`which autoreconf`" ]; then
        echo "Error: cannot build project because 'autoreconf' is not installed. You can install it by running 'apt-get install dh-autoreconf'."
        exit 1
    fi
    if [ ! -f /lib/x86_64-linux-gnu/libcap.so -o ! -f /usr/include/sys/capability.h ]; then
        echo "Error: cannot build fakeroot from source because of missing dependency 'libcap-dev'. You can install it by running 'apt-get install libcap-dev'."
        exit 1
    fi

    cd $target_dir
    if [ ! -d local ]; then
        mkdir local
    fi
    git clone https://github.com/mackyle/fakeroot.git fakeroot-src
    cd fakeroot-src
    libtoolize
    autoreconf -i
    ./configure --with-ipc=tcp --prefix=$target_dir/local
    make && make install
    if [ $? - ne 0 ]; then
        echo "ERROR: Failed to build fakeroot."
        exit 2
    fi
    write_build_path
    fakeroot=$target_dir/local/bin/fakeroot
}

function ensure_fakeroot {
    fakeroot=
    has_fakeroot
    if [ -z "$fakeroot" ]; then
        echo "Building fakeroot"
        build_fakeroot
    else
        echo "Using fakeroot from: $fakeroot"
    fi
}
