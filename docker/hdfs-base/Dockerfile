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

# Base image for hadoop/HDFS containers

ENV HADOOP_VERSION 2.7.1
ENV HADOOP_DIR /opt/hadoop-${HADOOP_VERSION}

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        tar \
        openjdk-7-jre-headless && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/


# Download and extract
RUN mkdir -p ${HADOOP_DIR} && \
    curl -Ls http://apache.mirrors.spacedump.net/hadoop/common/stable/hadoop-${HADOOP_VERSION}.tar.gz | tar xz --strip=1 -C ${HADOOP_DIR}


ENV JAVA_HOME /usr/lib/jvm/java-7-openjdk-amd64
ENV HADOOP_PREFIX ${HADOOP_DIR}
ENV HADOOP_CONF_DIR ${HADOOP_PREFIX}/etc/hadoop

WORKDIR ${HADOOP_DIR}
