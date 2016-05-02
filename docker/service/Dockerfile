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

FROM ufora/build
MAINTAINER Ronen Hilewicz <ronen@ufora.com>
# This image is used to run Ufora services on Ubuntu 14.04
#
COPY lib /opt/ufora
COPY logrotate /etc/logrotate.d/ufora
RUN mv /etc/cron.daily/logrotate /etc/cron.hourly/

RUN pip install -e /opt/ufora/packages/python
RUN mkdir /var/ufora

ENV PYTHONPATH=/opt/ufora
ENV ROOT_DATA_DIR=/var/ufora

VOLUME /var/ufora

ENTRYPOINT /opt/ufora/ufora/scripts/init/launcher

EXPOSE 30000 30002 30009 30010

