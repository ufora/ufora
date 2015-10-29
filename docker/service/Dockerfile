FROM ufora/build
MAINTAINER Ronen Hilewicz <ronen@ufora.com>
# This image is used to run Ufora services on Ubuntu 14.04
#
COPY lib /opt/ufora

RUN pip install -e /opt/ufora/packages/python
RUN mkdir /var/ufora

ENV PYTHONPATH=/opt/ufora
ENV ROOT_DATA_DIR=/var/ufora

VOLUME /var/ufora

ENTRYPOINT /opt/ufora/ufora/scripts/init/launcher

EXPOSE 30000 30002 30009 30010

