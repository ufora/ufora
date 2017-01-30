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

FROM ubuntu:14.04
MAINTAINER Ronen Hilewicz <ronen@ufora.com>
# This image is used to build Ufora packages on Ubuntu 14.04
# It includes a build of python that links against libtcmalloc.so

# APT package required to build and run Ufora
RUN apt-get update && apt-get install -y \
    bison \
    ccache \
    clang-3.5 \
    curl \
    gdb \
    gfortran \
    git \
    libblas-dev \
    libboost-date-time1.55-dev \
    libboost-filesystem1.55-dev \
    libboost-python1.55-dev \
    libboost-regex1.55-dev \
    libboost-thread1.55-dev \
    libboost-test1.55-dev \
    libclang-3.5-dev \
    libffi-dev \
    libgoogle-perftools-dev \
    liblapack-dev \
    libssl-dev \
    ocaml \
    pkg-config \
    psmisc \
    rsync \
    software-properties-common \
    unixodbc-dev \
    wget


# Python 2.7.9 - built from source to link against libtcmalloc
RUN apt-get build-dep -y python2.7 && \
    cd /tmp && \
    wget -nv https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tar.xz && \
    tar xf Python-2.7.9.tar.xz
RUN cd /tmp/Python-2.7.9 && \
    CC=clang-3.5 CXX=clang++-3.5 ./configure --prefix=/usr/local --enable-shared --with-libs='-ltcmalloc' --with-system-ffi --enable-ipv6 --enable-unicode=ucs4 --with-ensurepip=upgrade && \
    make && make install && ldconfig && \
    /usr/local/bin/python -m ensurepip && \
    rm -rf /tmp/Python-2.7.9*


# Required python modules
RUN pip install cython
RUN pip install --allow-unverified pyodbc\
    requests \
    boto \
    hdfs \
    nose \
    numpy \
    pyodbc \
    pexpect \
    pandas \
    scipy \
    wsaccel \
    psutil \
    jupyter


# NodeJS
RUN curl -sL https://deb.nodesource.com/setup_4.x | bash -
RUN apt-get install -y nodejs build-essential && \
    npm install -g coffee-script@1.10.0 mocha@2.3.3 forever@0.14.1


RUN echo "ccache -M 10G" >> /etc/bash.bashrc
ENV CCACHE_DIR /volumes/ccache
ENV CCACHE_COMPILERCHECK content


RUN ln -s /usr/bin/clang-3.5 /usr/bin/clang
RUN ln -s /usr/bin/clang++-3.5 /usr/bin/clang++
RUN mkdir /var/core

#install CUDA
RUN wget http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-repo-ubuntu1604_8.0.44-1_amd64.deb

RUN dpkg -i cuda-repo-ubuntu1604_8.0.44-1_amd64.deb

RUN apt-get update \
    && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install  --no-upgrade --no-install-recommends --yes \
        nvidia-367=367.48-0ubuntu1     \
        nvidia-367-dev=367.48-0ubuntu1 \
        nvidia-opencl-icd-367=367.48-0ubuntu1 \
        cuda-core-8-0=8.0.44-1         \
        cuda-cudart-8-0=8.0.44-1       \
        cuda-cudart-dev-8-0=8.0.44-1   \
        cuda-driver-dev-8-0=8.0.44-1   \
        cuda-drivers=367.48-1          \
        cuda-nvrtc-8-0=8.0.44-1        \
        libcuda1-367=367.48-0ubuntu1

ENV SHELL bash
