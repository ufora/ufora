---
layout: main
title: Releasing a Ufora Version
tagline: Instructions and checklist
category: develop
sort_index: 04
---

# Overview

A Ufora release represents a new version of the software. Each release consists of two artifacts:

1. A Python package of the `pyfora` module uploaded to [PyPi](https://pypi.python.org/pypi).
2. A docker image with the Ufora backend uploaded to [Docker Hub](https://hub.docker.com/).

The two pieces represent the client and server components, respectively, and their versions must match.
In addition, releases are marked with tags in the ufora github repo.



# Before a Release

When approaching a release, it it necessary to apply more strict control over commits that are accepted.
The closer we are to a release the higher the bar for admitting new commits and the rate of code changes decreases.


## Release Branch

In preparation for a release, a new release branch is created. Release branches allow for last-minute,
release-specific changes such as version number, documentation, release notes, as well as minor bug fixes.
Doing this work on a release branch frees up dev for receiving new features for the next planned release.
Release branches are always named: release-version. For example, the release branch for version 1.2 will be `origin/release-1.2`.


## Versioning Scheme

Versioning is based on [PEP 0440](https://www.python.org/dev/peps/pep-0440/) and [Semantic Versioning](http://semver.org/).
Version numbers are of the form `major.minor` or `major.minor.patch`, and pre/post release versions may also be used.

- Major version increments represent substantial changes to the product and may not be compatible with prior major versions.
- Minor version releases represent additional functionality that is backward compatible with prior releases within the same major version.
    Clients can expect their existing code to continue to work after a minor release update.
    New features and options may become available, and some functionality may be marked as deprecated,
    but existing code continues to work.
- Patches represent bug fixes to a minor version and include no new features. The absence of a patch
    number implies zero.
- Pre release versions precede planned versions. They can include features that aren't fully stabilized
    and may contain known bugs that are planned to be fixed before the release.
    Pre-release version are identified by a letter followed by a positive integer.
    The letters used are either `a` for alpha releases, `b` for beta releases, or `rc` for release-candidates
    (e.g. 0.3a1, 2.0rc2, etc.).
- Post release versions may be used to address minor peripheral errors that do not affect the released
    software (e.g. corrections or additions to release notes, documentation, etc.). They are identified by
    a post-release segment of the form `.postN` (e.g. `1.2.post1`).

**Note:** Major version zero is used during initial development before the public API is considered stable.
      Breaking changes *may* occur between minor versions.


## Version File

The current version is stored in the repo at `/packages/python/pyfora/_version.py`.
The file consists of a single line of the form:

    __version__ = '0.1.1'

This variable is directly exposed by `pyfora/__init__.py` and is also read by setup.py during packaging and installation.


## Release Notes

To make it easy for clients to understand what changes and/or bug fixes are included in a release,
we maintain a file that tracks these changes - `/packages/python/NEWS.txt`.
The file is cumulative and each new release adds a new section at the top - above the prior release.
Under each release section is a bullet list of features and bug fixes included in the release.



# Publishing a Release

## Merge the Release Branch

After making all code and documentation updates to support the release, merge the release branch to `origin/master`.
All releases are tagged in GitHub and release tags should all be on commits in master.


## Build and Package

Checkout the commit to be released - it should be at the HEAD of origin/master - and build it.
After the build completes successfully, run the following command from the root of the repo:

    $ ufora/scripts/package/create-package.sh -v <version> -d <dest>

Where `<version>` is the release version, and `<dest>` is a directory where the package will be placed.
If you are building in docker, make sure you use a directory shared with the host file-system for
easy access to the produced package.
This command will create a tarball named `ufora-<version>.tar.gz` in the `<dest>` directory.


## Build and Push a Docker Image

Copy the package tarball to a new directory and unpack it. For example:

    $ cd /tmp
    $ cp ~/volumes/ufora-packages/ufora-0.1.tar.gz .
    $ tar xf ufora-0.1.tar.gz

Go into the unpacked directory and run:

    $ sudo docker build -t ufora/service:<version> .

Where `<version>` is the release version. This will take a few seconds to complete.
Once completed, you can upload the newly created image to Docker Hub by running:

    $ sudo docker push ufora/service:<version>

**Note:** The last command requires that you have a Docker Hub account and that your account has permission to push to the ufora/service repo.
If you don't have an account, you can create one at https://hub.docker.com/.
Contact ronen@ufora.com for push permissions.

With each new release we also update the image tagged 'latest':

    $ sudo docker build -t ufora/service:latest
    $ sudo docker push ufora/service:latest


## Build and Upload the pyfora Package

To upload a pyfora package to PyPi, you will need an account at [pypi.python.org](https://pypi.python.org)
with permissions to upload the pyfora package.
After creating an account, contact ronen@ufora.com for permissions.

**Important:** Once a version is uploaded to PyPi it cannot be updated!
    If you made a mistake and uploaded the wrong package you will have to increment the version number
    in order to upload a new package.
    So double check that you are, in fact, on the right branch and the right commit before running the next command.

To build and upload the package, go to the /packages/python directory of your repo and run:

    $ python setup.py sdist bdist_wheel upload


# Create a Tag

From your repo run:

    $ git tag -a <version>
    $ git push origin <version>

Where `<version>` is the new release version.



# Release Checklist

1. Make sure `/packages/python/pyfora/_version.py` has the right version number.
2. Make sure release notes for the new version are in `/packages/python/NEWS.txt`.
3. Merge release branch to master
4. Build and package
5. Create and push a new docker image
6. Create and upload a new pyfora PyPi pakcage
7. Create and push a git tag
