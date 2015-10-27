#!/usr/bin/env bash

nodejs=
function find_nodejs {
    local nodepath=`which node`
    if [ -e "$nodepath" ]; then
        nodejs=$nodepath
        echo "Node.js installed in $nodejs"
    fi
}
function brew_install_nodejs {
    echo "Installing node.js. This could take a few minutes."
    brew install node
    find_nodejs
    find_npm
    if [ -z "$nodejs" -o -z "$npm" ]; then
        echo "ERROR: Unable to install node.js"
        exit 1
    fi
}

coffeescript=
function find_coffeescript {
    local coffeepath=`which coffee`
    if [ -e "$coffeepath" ]; then
        coffeescript=$coffeepath
        echo "Coffeescript installed in $coffeescript"
    fi
}
function npm_install_coffeescript {
    echo "Installing coffeescript. You may be prompted for your password."
    sudo npm install -g coffee-script --loglevel error
    find_coffeescript
    if [ -z "$coffeescript" ]; then
        echo "ERROR: Unable to install coffee-script"
        exit 1
    fi
}

npm=
function find_npm {
    local npmpath=`which npm`
    if [ -e "$npmpath" ]; then
        npm=$npmpath
        echo "Npm installed in $npm"
    fi
}

homebrew=
function find_homebrew {
    local brewpath=`which brew`
    if [ -e "$brewpath" ]; then
        homebrew=$brewpath
        echo "Homebrew installed in $homebrew"
    fi
}
function install_homebrew {
    echo "Installing homebrew - package manager for mac"
    ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"
    if [ $? -ne 0 -o ! -e "`which brew`" ]; then
        echo "ERROR: Failed to install homebrew."
        exit 1
    fi
}

pip=
function find_pip {
    local pippath=`which pip`
    if [ -e "$pippath" ]; then
        pip=$pippath
        echo "Pip installed in $pippath"
    fi
}
function install_pip {
    echo "Installing python package manager (pip). You may be prompted for your password."
    sudo easy_install -q pip
    if [ $? -ne 0 -o ! -e "`which pip`" ]; then
        echo "ERROR: Failed to install pip."
        exit 1
    fi
}

python_modules_to_install=
function find_python_modules {
    for i in requests docopt; do
        python -c "import $i" 2> /dev/null
        if [ $? -ne 0 ]; then
            python_modules_to_install="$python_modules_to_install $i"
        else
            echo "Python module '$i' already installed"
        fi
    done
}


find_nodejs
find_npm
find_coffeescript
find_python_modules
find_pip
if [ -z "$nodejs" -o -z "$npm" ]; then
    if [ "`uname -s`" == "Darwin" ]; then
        echo "Installing on Mac OS X"
        find_homebrew
        if [ -z "$homebrew" ]; then
            install_homebrew
        fi
        brew_install_nodejs
    elif [ "`uname -s`" == "Linux" ]; then
        echo "Linux installation coming soon..."
        exit 2
    fi
fi

if [ -z "$coffeescript" ]; then
    npm_install_coffeescript
fi

packageroot=$( cd $(dirname $0) ; pwd )
cd $packageroot
echo "Installing node.js modules. This could take a moment."
npm install --loglevel error
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install node modules."
    exit 1
fi


if [ ! -z "$python_modules_to_install" ]; then
    # we have python modules to install
    if [ -z "$pip" ]; then
        # first install pip, if not already installed
        install_pip
    fi

    echo "Installing python modules: $python_modules_to_install. You may be prompted for your password."
    sudo pip install -q $python_modules_to_install
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install python modules."
        exit 1
    fi
fi


if [ -d "/usr/local/bin" ]; then
    if [ -L "/usr/local/bin/fora-sync" ]; then
        # delete the symlink if it's already there
        rm "/usr/local/bin/fora-sync"
    fi
    ln -s $packageroot/bin/fora-sync /usr/local/bin/fora-sync
    if [ $? -ne 0 ]; then
        echo "ERROR: Can't create symlink /usr/local/bin/fora-sync."
    fi
fi

