Ufora Project Synchronization Tool
==================================

fora-sync
---------
fora-sync is a command line tool used to download projects from a Ufora account to a local directory, where they can be placed under source control, and upload them back.

Synopsis
--------
    fora-sync {upload, download} {project_name, all} [-u user] [-p password] [-c cluster] [-d directory] [-h] [-v]

Description
-----------
### Positional arguments:
These arguments MUST be provided at the command line.

| Argument            | Description                        |
|---------------------|------------------------------------|
| {upload, download}  | Upload from disk to a Ufora account or download from a Ufora account to disk.
| {project_name, all} | The name of the project to download or upload. Use 'all' to sync all projects.

### Optional arguments:
You may omit any or all of these arguments from the command line. If you do so, fora-sync will interactively prompt you for their values.

| Argument                          | Description                  |
|-----------------------------------|------------------------------|
| -u 'user', --user 'user'          | The Ufora user name.
| -p 'pwd', --password 'pwd'        | The Ufora account's password.
| -c 'cluster', --cluster 'cluster' | The Ufora cluster to connect to. In the format 'hostname[:port]'
| -d 'dir', --directory 'dir'       | Local directory to read/write projects from/to.

### Flags

| Argument                          | Description                  |
|-----------------------------------|------------------------------|
| -v, --version                     | Show the tool's version number and exit.
| -h, --help                        | Show the tool's help message and exit.


Examples
--------
To download all projects to the local direcoty ~/fora:

    fora-sync download all -d ~/fora
    
You will be prompted for your user name, password, and the Ufora cluster you wish to target. The output would look something like:

    user: john@fabrikon.com
    password:
    cluster: fabrikon.ufora.com
    
    Downloading...
        Project 'TutorialExamples'...    OK
        Project 'SalesModel'...    OK
    
To upload the project ~/fora/MyProject:

    fora-sync upload MyProject -d ~/fora -u john@fabrikon.com -c fabrikon.ufora.com
    
In this example, fora-sync will only prompt you for your password because all other arguments are provided at the command line.

    

Project Files
-------------
Project and their constituent scripts and modules are saved as .fora files.
A downloaded project named MyProject with a script called ComputeMe and a module named Util, will look like this:

- MyProject.fora
- MyProject/
    - ComputeMe.script.fora
    - Util.fora

Additionally, javascript modules are saved with .js extension, and dataset references are saved with .dataset.fora extension
Project submodules are downloaded to a subdirectory named after the parent module.

### Deleted Files
When running `fora-sync download`, if a module that had been previously downloaded was deleted from the project, fora-sync renames the local module file but does not delete it.

If the deleted module is called Util, then the file originally downloaded as Util.fora will be renamed to .Util.fora.deleted.




----
Copyright &copy; 2013-2014 Ufora Inc.

This file is part of fora-sync.
fora-sync or any part of it cannot be copied and/or distributed without the express permission of Ufora Inc.
