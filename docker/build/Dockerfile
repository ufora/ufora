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
    libclang-3.5-dev \
    libffi-dev \
    libgoogle-perftools-dev \
    liblapack-dev \
    libssl-dev \
    ocaml \
    pkg-config \
    psmisc \
    redis-server \
    rsync \
    software-properties-common \
    unixodbc-dev \
    wget


# Python 2.7.9 - built from source to link against libtcmalloc
# The python executable and libpython2.7.so are built in two separate 'make' steps
RUN apt-get build-dep -y python2.7 && \
    cd /tmp && \
    wget -nv https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tar.xz && \
    tar xf Python-2.7.9.tar.xz
RUN cd /tmp/Python-2.7.9 && \
    CC=clang-3.5 CXX=clang++-3.5 ./configure --prefix=/usr/local --enable-shared --with-libs='-ltcmalloc' --with-system-ffi --enable-ipv6 --enable-unicode=ucs2 --with-ensurepip=upgrade && \
    make && make install && ldconfig && \
    /usr/local/bin/python -m ensurepip


# Required python modules
RUN pip install --allow-unverified pyodbc\
    requests==2.2.1 \
    bcrypt \
    boto \
    hdfs \
    cherrypy \
    docopt \
    fabric \
    markdown \
    nose \
    numpy \
    paramiko \
    py-dateutil \
    pygithub3 \
    pyOpenSSL \
    pyodbc \
    pytz \
    redis \
    selenium \
    service_identity \
    simplejson \
    twisted \
    pyyaml \
    virtualenv


# NodeJS
RUN curl -sL https://deb.nodesource.com/setup | bash -
RUN apt-get install -y nodejs build-essential && \
    npm install -g coffee-script mocha forever@0.11.1 bower

RUN echo "/etc/init.d/redis-server start" >> /etc/bash.bashrc
RUN echo "ccache -M 10G" >> /etc/bash.bashrc
ENV CCACHE_DIR /volumes/ccache
ENV CCACHE_COMPILERCHECK content

RUN ln -s /usr/bin/clang-3.5 /usr/bin/clang
RUN ln -s /usr/bin/clang++-3.5 /usr/bin/clang++

RUN rm -rf /usr/local/lib/python2.7/site-packages/selenium/webdriver/firefox/x86
