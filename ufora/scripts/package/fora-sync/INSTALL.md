Fora-sync Installation Guide
============================

Quick Start
-----------
Fora-sync packages follow the naming scheme 'fora-sync-{version}.tar.gz'.
To install a package on your machine:

1. Copy the package to a directory into which you'd like to run fora-sync.

   For example: `cp fora-sync-{version}.tar.gz ~/ufora`
   
2. Unpack the package: `tar xvfz fora-sync-{version}.tar.gx`

   The tarball will extract into a new directory called 'fora-sync-{version}' (e.g. fora-sync-0.1.0)

3. Run the installation script: `fora-sync-{version}/install.sh`

   The installer will download and install all required packages. Depending on what's already installed on your machine, this may take several minutes, and may ask for your password.
   
   The installer also creates a symbolic link to fora-sync in /usr/local/bin.
   
4. Create a local directory for your fora projects (e.g. ~/fora)

5. Test the installation: `fora-sync download all -d ~/fora`

   Assuming you have a Ufora account that contains one or more projects, you should now see them saved in the ~/fora directory.
   
   

System Requirements
-------------------
Fora-sync is currently availble for Mac OS X clients only.


Dependencies
------------
The fora-sync installer checks for the existence of all required packages and installs ones that are missing.

The list of dependencies is:

- __node.js__: a non-blocking application development framework built on Chrome's JavaScript runtime.
- __coffee-script__: a convenient little language that compiles to JavaScript.
- __python modules__:
    - __pip__: python package manager
    - __requests__: an HTTP library
    - __docopt__: command-line argument parser
- __homebrew__: a package manager for Mac. Used to install node.js if not already installed.


----
Copyright &copy; 2013-2014 Ufora Inc.

This file is part of fora-sync.
fora-sync or any part of it cannot be copied and/or distributed without the express permission of Ufora Inc.
