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

import boto.ec2
import boto.exception
import datetime
import os
import time

from pyfora import __version__ as pyfora_version
from pyfora import TimeoutError


def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

def get_aws_credentials():
    key = os.getenv('AWS_ACCESS_KEY_ID')
    secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    if key and secret:
        return '-e AWS_ACCESS_KEY_ID=%s -e AWS_SECRET_ACCESS_KEY=%s' % (key, secret)

    return ''

class Launcher(object):
    ufora_security_group_name = 'ufora'
    ufora_security_group_description = 'ufora instances'
    ubuntu_images = {
        'ap-southeast-1': 'ami-e8f1c1ba',
        'ap-southeast-2': 'ami-7163104b',
        'ap-northeast-1': 'ami-8d6d9d8d',
        'eu-west-1': 'ami-5da23a2a',
        'eu-central-1': 'ami-b6cff2ab',
        'sa-east-1': 'ami-55883348',
        'us-east-1': 'ami-d85e75b0',
        'us-west-1': 'ami-d16a8b95',
        'us-west-2': 'ami-6989a659'
        }
    user_data_template = '''#!/bin/bash
    apt-get update
    apt-get install -y docker.io
    docker pull ufora/service:{image_version}
    if [ -d /mnt ]; then
        LOG_DIR=/mnt/ufora
    else
        LOG_DIR=/var/ufora
    fi
    mkdir $LOG_DIR
    OWN_PRIVATE_IP=`curl -s http://169.254.169.254/latest/meta-data/local-ipv4`
    docker run -d --name {container_name} \
        -e UFORA_WORKER_OWN_ADDRESS=$OWN_PRIVATE_IP \
        {aws_credentials} \
        {container_env} {container_ports} \
        -v $LOG_DIR:/var/ufora ufora/service:{image_version}
    '''
    def __init__(self,
                 region,
                 vpc_id=None,
                 subnet_id=None,
                 security_group_id=None,
                 instance_type=None,
                 open_public_port=False):
        assert vpc_id is None or subnet_id is not None
        self.region = region
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.security_group_id = security_group_id
        self.instance_type = instance_type
        self.open_public_port = open_public_port
        self.ec2 = None


    def launch_manager(self, ssh_key_name, spot_request_bid_price=None):
        instances = self.launch_instances(1,
                                          ssh_key_name,
                                          self.user_data_for_manager(),
                                          spot_request_bid_price)
        assert len(instances) == 1

        self.wait_for_instances(instances, timeout=300)

        instance = instances[0]
        if instance.state == 'running':
            self.tag_instance(instance, "ufora manager")
        else:
            raise Exception("Instance failed to start: " + instance.id)
        return instance


    def launch_workers(self,
                       count,
                       ssh_key_name,
                       manager_instance_id,
                       spot_request_bid_price=None):
        instances = self.launch_instances(count,
                                          ssh_key_name,
                                          self.user_data_for_worker(manager_instance_id),
                                          spot_request_bid_price)
        self.wait_for_instances(instances)
        for instance in instances:
            self.tag_instance(instance, 'ufora worker')
        return instances


    def get_reservations(self):
        if not self.connected:
            self.connect()

        filters = {'tag:Name': 'ufora*'}
        reservations = self.ec2.get_all_reservations(filters=filters)
        return reservations


    def launch_instances(self,
                         count,
                         ssh_key_name,
                         user_data,
                         spot_request_bid_price=None):
        assert self.instance_type is not None
        if not self.connected:
            self.connect()

        network_interfaces = self.create_network_interfaces()
        classic_security_groups = None if self.vpc_id else [self.get_security_group_name()]
        request_args = {
            'image_id': self.ubuntu_images[self.region],
            'instance_type': self.instance_type,
            'key_name': ssh_key_name,
            'user_data': user_data,
            'security_groups': classic_security_groups,
            'network_interfaces': network_interfaces
            }
        if spot_request_bid_price:
            ts = timestamp()
            spot_requests = self.ec2.request_spot_instances(
                price=spot_request_bid_price,
                count=count,
                availability_zone_group=ts,
                launch_group=ts,
                **request_args)
            fulfilled, unfulfilled = self.wait_for_spot_instance_requests(spot_requests)
            assert len(fulfilled) == count or len(unfulfilled) == count
            if len(fulfilled) == 0:
                return []
            return self.ec2.get_only_instances(instance_ids=[r.instance_id for r in fulfilled])
        else:
            reservation = self.ec2.run_instances(
                min_count=count,
                max_count=count,
                **request_args
                )
            return reservation.instances


    def user_data_for_manager(self):
        return self.user_data_template.format(
            aws_credentials=get_aws_credentials(),
            container_name='ufora_manager',
            container_env='',
            container_ports='-p 30000:30000 -p 30002:30002 -p 30009:30009 -p 30010:30010',
            image_version=pyfora_version)


    def user_data_for_worker(self, manager_instance_id):
        manager_address = self.get_instance_internal_ip(manager_instance_id)
        return self.user_data_template.format(
            aws_credentials=get_aws_credentials(),
            container_name='ufora_worker',
            container_env='-e UFORA_MANAGER_ADDRESS='+manager_address,
            container_ports='-p 30009:30009 -p 30010:30010',
            image_version=pyfora_version)


    @staticmethod
    def wait_for_instances(instances, timeout=None):
        t0 = time.time()
        while any(i.state == 'pending' for i in instances):
            if timeout and time.time() > t0 + timeout:
                raise TimeoutError(
                    "Timed out waiting for instances to start: " + [i.id for i in instances]
                    )
            time.sleep(5)
            for i in instances:
                if i.state == 'pending':
                    i.update()
        return True


    @staticmethod
    def tag_instance(instance, tag_prefix):
        instance.add_tag('Name', "%s - %s" % (tag_prefix, timestamp()))


    @property
    def connected(self):
        return self.ec2 is not None


    def connect(self):
        if self.region is None:
            self.ec2 = boto.connect_ec2()
        else:
            self.ec2 = boto.ec2.connect_to_region(self.region)

        if self.security_group_id is None:
            self.security_group_id = self.find_or_create_ufora_security_group()


    def create_network_interfaces(self):
        if self.vpc_id is None:
            return None

        interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(
            subnet_id=self.subnet_id,
            groups=[self.security_group_id],
            associate_public_ip_address=True
            )
        return boto.ec2.networkinterface.NetworkInterfaceCollection(interface)


    def get_security_group_name(self):
        groups = self.ec2.get_all_security_groups(group_ids=[self.security_group_id])
        assert len(groups) == 1
        return groups[0].name


    def wait_for_spot_instance_requests(self, requests, timeout=None):
        t0 = time.time()
        pending_states = ['pending-evaluation', 'pending-fulfillment']
        pending = {r.id: r for r in requests}
        fulfilled = {}
        unfulfilled = {}

        while len(pending) > 0:
            if timeout and time.time() > t0 + timeout:
                raise TimeoutError(
                    "Timed out waiting for spot instances to be fulfilled.",
                    fulfilled=fulfilled,
                    unfulfilled=unfulfilled,
                    pending=pending
                    )

            time.sleep(5)
            spot_requests = self.ec2.get_all_spot_instance_requests(
                request_ids=pending.keys()
                )
            for request in spot_requests:
                if request.state == 'active':
                    fulfilled[request.id] = request
                    del pending[request.id]
                elif request.state != 'open' or request.status.code not in pending_states:
                    unfulfilled[request.id] = request
                    del pending[request.id]
        return (fulfilled.values(), unfulfilled.values())


    def get_instance_internal_ip(self, instance_id):
        reservations = self.ec2.get_all_instances(instance_ids=[instance_id])
        assert len(reservations) == 1
        assert len(reservations[0].instances) == 1

        instance = reservations[0].instances[0]
        return instance.private_ip_address


    def find_or_create_ufora_security_group(self):
        security_group = self.find_ufora_security_group()
        if security_group is None:
            security_group = self.create_ufora_security_group()
        if self.open_public_port:
            security_group.authorize(cidr_ip='0.0.0.0/0',
                                     ip_protocol='tcp',
                                     from_port=30000,
                                     to_port=30000)
        return security_group.id


    def find_ufora_security_group(self):
        filters = None
        if self.vpc_id is not None:
            filters = {'vpc-id': self.vpc_id}
        try:
            groups = self.ec2.get_all_security_groups(
                groupnames=[self.ufora_security_group_name],
                filters=filters
                )
        except boto.exception.EC2ResponseError as e:
            if e.error_code == 'InvalidGroup.NotFound':
                return None
            raise

        assert len(groups) < 2, "More than one ufora security groups exist"

        if len(groups) == 0:
            return None

        return groups[0]


    def create_ufora_security_group(self):
        security_group = self.ec2.create_security_group(
            name=self.ufora_security_group_name,
            description=self.ufora_security_group_description,
            vpc_id=self.vpc_id
            )
        security_group.authorize(src_group=security_group,
                                 ip_protocol='tcp',
                                 from_port=30002,
                                 to_port=30010)
        security_group.authorize(cidr_ip='0.0.0.0/0',
                                 ip_protocol='tcp',
                                 from_port=22,
                                 to_port=22)
        return security_group
