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
import itertools
import os
import time

from pyfora import __version__ as pyfora_version
from pyfora import TimeoutError


def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

def get_aws_access_key_id():
    return os.getenv('AWS_ACCESS_KEY_ID')

def get_aws_secret_access_key():
    return os.getenv('AWS_SECRET_ACCESS_KEY')

def get_aws_credentials_docker_env():
    key = get_aws_access_key_id()
    secret = get_aws_secret_access_key()
    if key and secret:
        return '--env AWS_ACCESS_KEY_ID=%s --env AWS_SECRET_ACCESS_KEY=%s' % (key, secret)

    return ''

user_data_file = '''#!/bin/bash
export AWS_ACCESS_KEY_ID={aws_access_key}
export AWS_SECRET_ACCESS_KEY={aws_secret_key}
export AWS_DEFAULT_REGION={aws_region}
export OWN_INSTANCE_ID=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
export OWN_PRIVATE_IP=`curl -s http://169.254.169.254/latest/meta-data/local-ipv4`
export SET_STATUS="aws ec2 create-tags --resources $OWN_INSTANCE_ID --tags Key=status,Value="
export COMMIT_TO_BUILD={commit_to_build}
export NEEDS_CUDA={needs_cuda}
export IMAGE_VERSION={image_version}

if [[ $NEEDS_CUDA ]]
then
    export DOCKER="sudo nvidia-docker"
else
    export DOCKER="sudo docker"
fi

if [ -d /mnt ]; then
    LOG_DIR=/mnt/ufora
else
    LOG_DIR=/var/ufora
fi
mkdir -p $LOG_DIR

BUILD_DIR=/home/ubuntu/build
mkdir -p $BUILD_DIR

function install_docker_and_prerequisites {{
    apt-get update
    apt-get install -y awscli

    #docker installation for docker 1.9
    ${{SET_STATUS}}'installing docker 1.9'

    apt-get install -y git apt-transport-https ca-certificates
    apt-get update

    apt-get upgrade -y
    apt-get install -y --force-yes linux-image-extra-`uname -r` linux-headers-`uname -r` linux-image-`uname -r`

    apt-get install apparmor

    sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" > /etc/apt/sources.list.d/docker.list
    apt-get update

    apt-get install -y docker-engine
    service docker start

    #verify we have docker
    docker run hello-world
    if [ $? -ne 0 ]; then
        ${{SET_STATUS}}'install failed'
        exit 1
    fi
    }}


function docker_run_build {{
    FLAGS=
    ARGS=
    for var in "$@"
    do
        if [[ $var == -* ]]
        then
            FLAGS="$FLAGS $var"
        else
            ARGS="$ARGS $var"
        fi
    done

    BUILD_IMAGE_VERSION=`md5sum $BUILD_DIR/ufora/docker/build/Dockerfile|awk '{{print $1}}'`

    $DOCKER run $FLAGS \\
        --env UFORA_WORKER_OWN_ADDRESS=$OWN_PRIVATE_IP \\
        --workdir=/volumes/ufora \\
        {aws_credentials} \\
        {container_env} {container_ports} \\
        --privileged=true \\
        --volume $LOG_DIR:/var/ufora \\
        --volume $BUILD_DIR:/volumes \\
        --env PYTHONPATH=/volumes/ufora \\
        --env ROOT_DATA_DIR=$LOG_DIR \\
        ufora/build:$BUILD_IMAGE_VERSION \\
        $ARGS
    if [ $? -ne 0 ]; then
        ${{SET_STATUS}}'launch failed'
        exit 1
    fi
    }}

function run_ufora_service {{
    if [ "$IMAGE_VERSION" != "local" ]; then
        ${{SET_STATUS}}'pulling docker image'
        $DOCKER pull ufora/service:$IMAGE_VERSION
        if [ $? -ne 0 ]; then
            ${{SET_STATUS}}'pull failed'
            exit 1
        fi
    fi

    ${{SET_STATUS}}'launching service'

    $DOCKER run --detach --name {container_name} \\
        --env UFORA_WORKER_OWN_ADDRESS=$OWN_PRIVATE_IP \\
        --privileged=true \\
        {aws_credentials} \\
        {container_env} {container_ports} \\
        --volume $LOG_DIR:/var/ufora ufora/service:$IMAGE_VERSION
    if [ $? -ne 0 ]; then
        ${{SET_STATUS}}'launch failed'
        exit 1
    fi
    }}

function stop_ufora_service {{
    $DOCKER stop {container_name}
    if [ $? -ne 0 ]; then
        exit 1
    fi

    $DOCKER rm {container_name}
    if [ $? -ne 0 ]; then
        exit 1
    fi
    }}

function build_local_docker_image {{
    cd /tmp
    rm -rf ufora-*
    tar xf /home/ubuntu/ufora-*.tar.gz
    sudo docker build -t ufora/service:local ufora-*/
    if [ $? -ne 0 ]; then
        exit 1
    fi
    }}

function install_cuda {{
    ${{SET_STATUS}}'installing CUDA'

    wget http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1404/x86_64/cuda-repo-ubuntu1404_7.5-18_amd64.deb
    dpkg -i cuda-repo-ubuntu1404_7.5-18_amd64.deb

    apt-get update
    apt-get upgrade -y
    apt-get install -y --no-install-recommends --force-yes cuda-nvrtc-7-5 cuda-cudart-7-5 cuda-drivers cuda-core-7-5 cuda-driver-dev-7-5

    curl -fsSL https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.0-beta/nvidia-docker_1.0.0.beta-1_amd64.deb -o /tmp/nvidia-docker.deb
    dpkg -i /tmp/nvidia-docker.deb
    }}

function build_ufora {{
    ${{SET_STATUS}}'cloning git repo'
    cd $BUILD_DIR
    git clone https://github.com/ufora/ufora.git

    cd $BUILD_DIR/ufora
    git checkout {commit_to_build}
    if [ $? -ne 0 ]; then
        ${{SET_STATUS}}'checking out {commit_to_build} failed'
        exit 1
    fi

    BUILD_IMAGE_VERSION=`md5sum $BUILD_DIR/ufora/docker/build/Dockerfile|awk '{{print $1}}'`

    ${{SET_STATUS}}'pulling docker image'
    $DOCKER pull ufora/build:$BUILD_IMAGE_VERSION
    if [ $? -ne 0 ]; then
        ${{SET_STATUS}}'pull failed'
        exit 1
    fi

    ${{SET_STATUS}}'building codebase'
    docker_run_build --rm ./waf configure
    docker_run_build --rm python ufora/scripts/resetAxiomSearchFunction.py
    docker_run_build --rm ./waf install
    docker_run_build --rm python ufora/scripts/rebuildAxiomSearchFunction.py
    docker_run_build --rm ./waf install

    run_built_service
    }}

function run_built_service {{
    ${{SET_STATUS}}'starting services'

    echo "#!/bin/bash" > $BUILD_DIR/ufora/start.sh
    echo "ufora/scripts/init/start" >> $BUILD_DIR/ufora/start.sh
    echo "ufora/scripts/init/ufora-worker start" >> $BUILD_DIR/ufora/start.sh
    echo "sleep infinity" >> $BUILD_DIR/ufora/start.sh
    chmod +x $BUILD_DIR/ufora/start.sh

    docker_run_build --detach --name=ufora_manager ./start.sh
}}

function post_reboot {{
    echo "UFORA post-reboot script running."

    if [ -z $COMMIT_TO_BUILD ]; then
        run_ufora_service
    else
        build_ufora
    fi

    ${{SET_STATUS}}'ready'
}}

#this is the main entrypoint, called when the instance is booted
#we check whether we need to install CUDA, in which case we have to
#write a bootscript into /etc/rc.local to continue the installation process.
function on_cloud_init {{
    install_docker_and_prerequisites

    if [[ $NEEDS_CUDA ]]; then
        install_cuda

        echo "#!/bin/bash" > /etc/rc.local
        echo "#autogenerated boot script for UFORA instance" >> /etc/rc.local
        echo "source /home/ubuntu/ufora_setup.sh" >> /etc/rc.local
        echo "post_reboot" >> /etc/rc.local
        echo "exit 0" >> /etc/rc.local

        ${{SET_STATUS}}'REBOOTING'
        reboot now
    else
        post_reboot
    fi
}}
'''

class Launcher(object):
    ufora_ssh_security_group_name = 'pyfora ssh'
    ufora_open_security_group_name = 'pyfora open'
    ufora_security_group_description = 'pyfora instances'
    ubuntu_images_paravirtual_ssd = {
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
    ubuntu_images_hvm_ssd = {
        'ap-northeast-1': 'ami-2f615b41',
        'ap-southeast-1': 'ami-d6509fb5',
        'ap-southeast-2': 'ami-93dafef0',
        'eu-central-1': 'ami-56f4ec3a',
        'eu-west-1': 'ami-9c77c1ef',
        'sa-east-1': 'ami-051b9b69',
        'us-east-1': 'ami-35d6f95f',
        'us-west-1': 'ami-06235566',
        'us-west-2': 'ami-abc620cb'
        }

    def getUserDataTemplate(self):
        user_data_template = (
            "#!/bin/bash\n" +
            "cat >/home/ubuntu/ufora_setup.sh <<'EOL'\n" +
            user_data_file + "\nEOL\n"
            )

        user_data_template += 'chown ubuntu:ubuntu /home/ubuntu/ufora_setup.sh\n'
        user_data_template += "source /home/ubuntu/ufora_setup.sh\n"
        user_data_template += "on_cloud_init\n"

        return user_data_template

    def __init__(self,
                 name,
                 region=None,
                 vpc_id=None,
                 subnet_id=None,
                 security_group_id=None,
                 instance_type=None,
                 open_public_port=False,
                 commit_to_build=None):
        assert vpc_id is None or subnet_id is not None
        self.cluster_name = name
        self.region = region
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.security_group_id = security_group_id
        self.instance_type = instance_type
        self.open_public_port = open_public_port
        self.ec2 = None
        self.commit_to_build = commit_to_build

    def launch_manager(self, ssh_key_name, spot_request_bid_price=None, callback=None):
        if not self.connected:
            self.connect()

        user_data = self.user_data_for_manager()

        instances = self.launch_instances(1,
                                          ssh_key_name,
                                          user_data,
                                          spot_request_bid_price,
                                          callback=callback)
        instance = None
        if instances:
            self.wait_for_instances(instances, timeout=300, callback=callback)

            instance = instances[0]
            if instance.state == 'running':
                self.tag_instance(instance, "pyfora manager")
            else:
                raise Exception("Instance failed to start: " + instance.id)

        return instance


    def launch_workers(self,
                       count,
                       ssh_key_name,
                       manager_instance_id,
                       spot_request_bid_price=None,
                       callback=None):
        if not self.connected:
            self.connect()

        instances = self.launch_instances(count,
                                          ssh_key_name,
                                          self.user_data_for_worker(manager_instance_id),
                                          spot_request_bid_price,
                                          callback=callback)
        self.wait_for_instances(instances, callback=callback)
        for instance in instances:
            self.tag_instance(instance, 'pyfora worker')
        return instances


    def wait_for_services(self, instances, callback=None):
        assert self.connected
        pending = set(instances)
        ready = []
        failed = []

        while len(pending):
            toRemove = []
            for i in pending:
                i.update()
                if 'status' not in i.tags:
                    continue

                if i.tags['status'].endswith('failed'):
                    toRemove.append(i)
                    failed.append(i)
                elif i.tags['status'] == 'ready':
                    toRemove.append(i)
                    ready.append(i)

            for i in toRemove:
                pending.remove(i)

            status = {}
            for i in itertools.chain(pending, ready, failed):
                if 'status' not in i.tags:
                    # there is no status while the instance installs the AWS cli
                    status_name = 'installing dependencies'
                else:
                    status_name = i.tags['status']

                if status_name not in status:
                    status[status_name] = []
                status[status_name].append(i)
            if callback:
                callback(status)

            if len(pending):
                time.sleep(1)

        return len(failed) == 0


    def get_reservations(self):
        if not self.connected:
            self.connect()

        filters = {'tag:pyfora_cluster': self.cluster_name}
        reservations = self.ec2.get_all_reservations(filters=filters)
        instances = {i.id: i for r in reservations for i in r.instances}

        spot_requests = [
            r for r in self.ec2.get_all_spot_instance_requests(filters=filters)
            if r.state != 'cancelled'
            ]
        spot_instance_ids = [r.instance_id for r in spot_requests
                             if r.instance_id and r.instance_id not in instances]
        unfulfilled_spot_requests = [r for r in spot_requests if not r.instance_id]

        all_instances = instances.values() + \
                        self.ec2.get_only_instances(
                            instance_ids=spot_instance_ids
                            ) if spot_instance_ids else []
        return {
            'instances': all_instances,
            'unfulfilled_spot_requests': unfulfilled_spot_requests
            }


    def launch_instances(self,
                         count,
                         ssh_key_name,
                         user_data,
                         spot_request_bid_price=None,
                         callback=None):
        assert self.instance_type is not None
        assert self.connected

        network_interfaces = self.create_network_interfaces()
        classic_security_groups = None if self.vpc_id else [self.get_security_group_name()]

        if self.instance_type[:2] in ("c3", "m3"):
            image_id = self.ubuntu_images_paravirtual_ssd[self.region]
        else:
            image_id = self.ubuntu_images_hvm_ssd[self.region]

        #ensure that we allocate enough space to install everything
        dev_sda1 = boto.ec2.blockdevicemapping.BlockDeviceType(
            size=15,
            delete_on_termination=True)
        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        bdm['/dev/sda1'] = dev_sda1

        request_args = {
            'image_id': image_id,
            'instance_type': self.instance_type,
            'key_name': ssh_key_name,
            'user_data': user_data,
            'security_groups': classic_security_groups,
            'network_interfaces': network_interfaces,
            'block_device_map': bdm
            }
        if spot_request_bid_price:
            ts = timestamp() if count > 1 else None
            spot_requests = self.ec2.request_spot_instances(
                price=spot_request_bid_price,
                count=count,
                availability_zone_group=ts,
                launch_group=ts,
                **request_args)
            fulfilled, unfulfilled = self.wait_for_spot_instance_requests(spot_requests,
                                                                          callback=callback)
            self.create_tags(list(r.id for r in itertools.chain(fulfilled, unfulfilled)),
                             'pyfora_cluster',
                             self.cluster_name)
            if len(fulfilled) == 0:
                return []

            return self.ec2.get_only_instances(instance_ids=[r.instance_id for r in fulfilled])
        else:
            reservation = self.ec2.run_instances(
                min_count=count,
                max_count=count,
                **request_args
                )
            self.create_tags([i.id for i in reservation.instances],
                             'pyfora_cluster',
                             self.cluster_name)
            return reservation.instances


    def get_format_args(self, updates):
        assert self.connected

        args = {
            'aws_access_key': self.ec2.provider.access_key,
            'aws_secret_key': self.ec2.provider.secret_key,
            'aws_region': self.region,
            'aws_credentials': get_aws_credentials_docker_env(),
            'container_env': '',
            'image_version': pyfora_version,
            'commit_to_build': str(self.commit_to_build) if self.commit_to_build is not None else "",
            "needs_cuda": "1" if self.instance_type[:2] == "g2" else ""
            }

        args.update(updates)
        return args


    def user_data_for_manager(self):
        format_args = self.get_format_args({
            'container_name': 'ufora_manager',
            'container_ports': '--publish 30000:30000 --publish 30002:30002 --publish 30009:30009 --publish 30010:30010',
            })
        return self.getUserDataTemplate().format(**format_args)


    def user_data_for_worker(self, manager_instance_id):
        manager_address = self.get_instance_internal_ip(manager_instance_id)
        format_args = self.get_format_args({
            'container_name': 'ufora_worker',
            'container_env': '--env UFORA_MANAGER_ADDRESS=' + manager_address,
            'container_ports': '--publish 30009:30009 --publish 30010:30010'
            })
        return self.getUserDataTemplate().format(**format_args)


    @staticmethod
    def wait_for_instances(instances, timeout=None, callback=None):
        t0 = time.time()
        while any(i.state == 'pending' for i in instances):
            if timeout and time.time() > t0 + timeout:
                raise TimeoutError(
                    "Timed out waiting for instances to start: " + [i.id for i in instances]
                    )
            time.sleep(1)
            status = {}
            for i in instances:
                if not i.state in status:
                    status[i.state] = []
                status[i.state].append(i.id)

                if i.state == 'pending':
                    i.update()
            if callback:
                callback(status)
        return True


    def tag_instance(self, instance, tag_prefix):
        self.create_tags(instance.id, 'Name', "%s - %s" % (tag_prefix, timestamp()))


    def create_tags(self, object_ids, tag_name, tag_value):
        self.ec2.create_tags(object_ids, {tag_name: tag_value})


    @property
    def connected(self):
        return self.ec2 is not None


    def connect(self):
        if self.region is None:
            self.ec2 = boto.connect_ec2()
        else:
            self.ec2 = boto.ec2.connect_to_region(self.region)

        assert self.ec2 is not None

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


    def wait_for_spot_instance_requests(self, requests, timeout=None, callback=None):
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

            time.sleep(1)
            spot_requests = self.ec2.get_all_spot_instance_requests(
                request_ids=pending.keys()
                )
            status = {}
            for request in spot_requests:
                status_key = '%s - %s' % (request.state, request.status.code)
                if status_key not in status:
                    status[status_key] = []
                status[status_key].append(request.id)
                if request.state == 'active':
                    fulfilled[request.id] = request
                    del pending[request.id]
                elif request.state != 'open' or request.status.code not in pending_states:
                    unfulfilled[request.id] = request
                    del pending[request.id]
            if callback:
                callback(status)

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
        return security_group.id


    def find_ufora_security_group(self):
        filters = None
        if self.vpc_id is not None:
            filters = {'vpc-id': self.vpc_id}
        try:
            groups = self.ec2.get_all_security_groups(
                groupnames=[self.security_group_name],
                filters=filters
                )
        except boto.exception.EC2ResponseError as e:
            if e.error_code == 'InvalidGroup.NotFound':
                return None
            raise

        assert len(groups) < 2, "More than one pyfora security groups exist"

        if len(groups) == 0:
            return None

        return groups[0]


    @property
    def security_group_name(self):
        return self.ufora_open_security_group_name if self.open_public_port \
               else self.ufora_ssh_security_group_name


    def create_ufora_security_group(self):
        security_group = self.ec2.create_security_group(
            name=self.security_group_name,
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
        if self.open_public_port:
            security_group.authorize(cidr_ip='0.0.0.0/0',
                                     ip_protocol='tcp',
                                     from_port=30000,
                                     to_port=30000)
        return security_group
