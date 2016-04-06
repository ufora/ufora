import argparse
import os
import subprocess
import sys
import threading
import time
from pyfora.aws.Launcher import Launcher


def get_region(region):
    region = region or os.getenv('PYFORA_AWS_EC2_REGION')
    if region is None:
        raise ValueError('EC2 region not specified')
    return region


def get_ssh_keyname(keyname):
    return keyname or os.getenv('PYFORA_AWS_SSH_KEYNAME')



class StatusPrinter(object):
    spinner = ['|', '/', '-', '\\']

    def __init__(self):
        self.spinner_index = 0
        self.last_message_len = 0
        self.last_message = ""

    def on_status(self, status):
        if len(status) == 1 and len(status.items()[0][1]) == 1:
            message_body = self.single_status_message(status)
        else:
            message_body = self.status_summary_message(status)

        isDifferent = (message_body != self.last_message)
        isFirst = self.last_message == ""

        self.last_message = message_body

        message = time.asctime() + " -- " + message_body + \
            ("" if isDifferent else " " + self.spinner[self.spinner_index])

        if isFirst:
            print message,

        if isDifferent:
            print ''
        else:
            print '\r',

        self.spinner_index = (self.spinner_index + 1) % len(self.spinner)

        message_len = len(message)
        if message_len < self.last_message_len:
            message = message + ' '*(self.last_message_len - message_len)
        self.last_message_len = message_len
        print message,
        sys.stdout.flush()

    def done(self):
        message = "Done" + ' '*self.last_message_len
        print ''
        print message
        print ''
        sys.stdout.flush()

    @staticmethod
    def failed():
        print ''
        print ''
        print 'Failed'
        sys.stdout.flush()



    @staticmethod
    def single_status_message(status):
        status_name, items = status.items()[0]
        return "%s: %s" % (items[0], status_name)


    @staticmethod
    def status_summary_message(status):
        return ', '.join(["%s (%d)" % (status_name, len(items))
                          for status_name, items in status.iteritems()])


def launcher_args(parsed_args):
    return {
        'region': get_region(parsed_args.ec2_region),
        'vpc_id': parsed_args.vpc_id,
        'subnet_id': parsed_args.subnet_id,
        'security_group_id': parsed_args.security_group_id
        }



def start_instances(args):
    assert args.num_instances > 0
    ssh_keyname = get_ssh_keyname(args.ssh_keyname)
    open_public_port = args.open_public_port or ssh_keyname is None
    if ssh_keyname is None and not args.yes_all:
        response = raw_input(
            "You are launching instances without specifying an ssh key-pair name.\n"
            "You will not be able to log into the launched instances.\n"
            "You can specify a key-pair using the --ssh-keyname option.\n"
            "Do you want to continue without a keypair (Y/n)? "
            )
        if response not in ('Y', 'y'):
            return

    launcher = Launcher(instance_type=args.instance_type,
                        open_public_port=open_public_port,
                        commit_to_build=args.commit,
                        **launcher_args(args))

    status_printer = StatusPrinter()
    print "Launching manager instance:"
    manager = launcher.launch_manager(ssh_keyname,
                                      args.spot_price,
                                      callback=status_printer.on_status)
    status_printer.done()

    print "Manager instance started:\n"
    print_instance(manager, 'manager')
    print ""
    if not args.open_public_port:
        print "To tunnel the pyfora HTTP port (30000) over ssh, run the following command:"
        print "    ssh -i <ssh_key_file> -L 30000:localhost:30000 ubuntu@%s\n" % manager.ip_address

    workers = []
    if args.num_instances > 1:
        print "Launching worker instance(s):"
        workers = launcher.launch_workers(args.num_instances-1,
                                          ssh_keyname,
                                          manager.id,
                                          args.spot_price,
                                          callback=status_printer.on_status)
        status_printer.done()
        print "Worker instance(s) started:"

    for worker in workers:
        print_instance(worker, 'worker')

    print "Waiting for services:"
    if launcher.wait_for_services([manager] + workers, callback=status_printer.on_status):
        status_printer.done()
    else:
        status_printer.failed()

def pad(s, ct):
    return s + " " * max(ct - len(s), 0)

def restart_instances(args):
    launcher = Launcher(**launcher_args(args))
    instances = running_or_pending_instances(launcher.get_reservations())
    identity_file = args.identity_file

    def restart_instance(instance):
        is_manager = 'manager' in instance.tags.get('Name', '')

        if is_manager:
            command = '"source ufora_setup.sh; \\$DOCKER stop ufora_manager; sudo rm -rf \\$LOG_DIR/*; \\$DOCKER start ufora_manager"'
        else:
            command = '"source ufora_setup.sh; \\$DOCKER stop ufora_worker; sudo rm -rf \\$LOG_DIR/*; \\$DOCKER start ufora_worker"'

        return (pad(instance.ip_address + "> ", 25), ssh_output(identity_file, instance.ip_address, command))

    for ip, res in parallel_for(instances, restart_instance):
        for line in res.split("\n"):
            print ip, line



def add_instances(args):
    launcher = Launcher(**launcher_args(args))
    manager = [i for i in running_or_pending_instances(launcher.get_reservations())
               if 'manager' in i.tags.get('Name', '')]
    if len(manager) > 1:
        print "There is more than one Manager instance. Can't add workers.", \
            "Managers:"
        for m in manager:
            print_instance(m)
        return 1
    elif len(manager) == 0:
        print "No manager instances are running. Can't add workers."
        return 1

    if args.num_instances < 1:
        print "--num-instances must be greater or equal to 1."
        return 1

    manager = manager[0]
    launcher.vpc_id = manager.vpc_id
    launcher.subnet_id = manager.subnet_id
    launcher.instance_type = manager.instance_type
    launcher.security_group_id = manager.groups[0].id

    print "Launching worker instance(s):"
    status_printer = StatusPrinter()
    workers = launcher.launch_workers(args.num_instances,
                                      manager.key_name,
                                      manager.id,
                                      args.spot_price,
                                      callback=status_printer.on_status)
    status_printer.done()

    print "Workers started:"
    for worker in workers:
        print_instance(worker, 'worker')

    print ""
    print "Waiting for services:"
    if launcher.wait_for_services(workers, callback=status_printer.on_status):
        status_printer.done()
    else:
        status_printer.failed()


def list_instances(args):
    launcher = Launcher(**launcher_args(args))
    reservations = launcher.get_reservations()
    count = sum(len(r.instances) for r in reservations)
    print "%d instance%s%s" % (
        count, 's' if count != 1 else '', ':' if count > 0 else ''
        )
    for r in reservations:
        for i in r.instances:
            print_instance(i)


def stop_instances(args):
    launcher = Launcher(**launcher_args(args))
    instances = running_or_pending_instances(launcher.get_reservations())
    count = len(instances)
    if count == 0:
        print "No running instances to stop"
        return

    verb = 'Terminating' if args.terminate else 'Stopping'
    print '%s %d instances:' % (verb, count)
    for i in instances:
        print_instance(i)
        if args.terminate:
            i.terminate()
        else:
            i.stop()


def scp(local_path, remote_path, host, identity_file):
    try:
        command = "scp -i %s %s ubuntu@%s:%s" % (
            identity_file,
            local_path,
            host,
            remote_path)
        subprocess.check_output(command, shell=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.output


def ssh(identity_file, host, command):
    try:
        subprocess.check_output("ssh -i %s ubuntu@%s %s" % (identity_file, host, command),
                                shell=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.output

def ssh_output(identity_file, host, command):
    try:
        return subprocess.check_output("ssh -i %s ubuntu@%s %s" % (identity_file, host, command),
                                shell=True)
    except subprocess.CalledProcessError as e:
        return e.output


def upload_package(package, instances, identity_file):
    def upload_to_instance(instance):
        return scp(package, '/home/ubuntu', instance.ip_address, identity_file)

    return parallel_for(instances, upload_to_instance)


def update_ufora_service(instances, identity_file):
    def build_on_instance(instance):
        command = '"source ufora_setup.sh; export IMAGE_VERSION=local; ' + \
            'stop_ufora_service; build_local_docker_image; run_ufora_service"'
        return ssh(identity_file, instance.ip_address, command)

    return parallel_for(instances, build_on_instance)


def parallel_for(collection, command):
    results = [None] * len(collection)
    def run_command(ix):
        results[ix] = command(collection[ix])

    threads = [threading.Thread(target=run_command, args=(i,))
               for i in xrange(len(collection))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results


def deploy_package(args):
    launcher = Launcher(**launcher_args(args))
    instances = running_instances(launcher.get_reservations())
    if len(instances) == 0:
        print "No running instances"
        return

    print "Running instances:"
    for i in instances:
        print_instance(i)
    print ''

    def is_failure(result):
        return isinstance(result, basestring)

    def any_failures(results):
        return any(is_failure(x) for x in results)

    def print_failures(results):
        for ix in xrange(len(results)):
            if is_failure(results[ix]):
                print instances[ix].id, "|", instances[ix].ip_address, ':', results[ix]

    print "Uploading package..."
    results = upload_package(args.package, instances, args.identity_file)
    if any_failures(results):
        print "Failed to upload package:"
        print_failures(results)
        return
    print "Package uploaded successfully"
    print ''

    print "Updating service..."
    results = update_ufora_service(instances, args.identity_file)
    if any_failures(results):
        print "Failed to update service:"
        print_failures(results)
        return
    print "Service updated successfully"


def running_instances(reservations):
    return instances_in_state(reservations, ('running',))


def running_or_pending_instances(reservations):
    return instances_in_state(reservations, ('running', 'pending'))


def instances_in_state(reservations, states):
    return [
        i for r in reservations
        for i in r.instances
        if i.state in states
        ]


def print_instance(instance, tag=None):
    output = "    %s | %s | %s" % (instance.id, instance.ip_address, instance.state)
    if tag is None and 'Name' in instance.tags:
        tag = 'manager' if 'manager' in instance.tags['Name'] else 'worker'

    tag = tag or ''
    if tag:
        output += " | " + tag
    print output

all_arguments = {
    'yes-all': {
        'args': ('-y', '--yes-all'),
        'kwargs': {
            'action': 'store_true',
            'help': 'Do not prompt user input. Answer "yes" to all prompts.'
            }
        },
    'ec2-region': {
        'args': ('--ec2-region',),
        'kwargs': {
            'default': 'us-east-1',
            'help': ('The EC2 region in which instances are launched. '
                     'Can also be set using the PYFORA_AWS_EC2_REGION environment variable. '
                     'Default: us-east-1')
            }
        },
    'num-instances': {
        'args': ('-n', '--num-instances'),
        'kwargs': {
            'type': int,
            'default': 1,
            'help': 'The number of instances to launch. Default: %(default)s'
            }
        },
    'ssh-keyname': {
        'args': ('--ssh-keyname',),
        'kwargs': {
            'help': ('The name of the EC2 key-pair to use when launching instances. '
                     'Can also be set using the PYFORA_AWS_SSH_KEYNAME environment variable.')
            }
        },
    'spot-price': {
        'args': ('--spot-price',),
        'kwargs': {
            'type': float,
            'help': ('Launch spot instances with specified max bid price. '
                     'On-demand instances are launch if this argument is omitted.')
            }
        },
    'instance-type': {
        'args': ('--instance-type',),
        'kwargs': {
            'default': 'c3.8xlarge',
            'help': 'The EC2 instance type to launch. Default: %(default)s'
            }
        },
    'vpc-id': {
        'args': ('--vpc-id',),
        'kwargs': {
            'help': ('The id of the VPC into which instances are launched. '
                     'EC2 Classic is used if this argument is omitted.')
            }
        },
    'subnet-id': {
        'args': ('--subnet-id',),
        'kwargs': {
            'help': ('The id of the VPC subnet into which instances are launched. '
                     'This argument must be specified if --vpc-id is used and is '
                     'ignored otherwise.')
            }
        },
    'security-group-id': {
        'args': ('--security-group-id',),
        'kwargs': {
            'help': ('The id of the EC2 security group into which instances are launched. '
                     'If omitted, a security group called "pyfora ssh" (or "pyfora open" '
                     'if --open-public-port is specified) is created. If a security group '
                     'with that name already exists, it is used as-is.')
            }
        },
    'open-public-port': {
        'args': ('--open-public-port',),
        'kwargs': {
            'action': 'store_true',
            'help': ('If specified, HTTP access to the manager machine will be open from '
                     'anywhere (0.0.0.0/0). Use with care! '
                     'Anyone will be able to connect to your cluster. '
                     "As an alternative, considering tunneling pyfora's HTTP port (30000) "
                     'over SSH using the -L argument to the `ssh` command.')
            }
        },
    'commit': {
        'args': ('--commit',),
        'kwargs': {
            'help': ('Run the backend services from a specified commit in the ufora/ufora '
                     'GitHub repository.')
            }
        },
    'terminate': {
        'args': ('--terminate',),
        'kwargs': {
            'action': 'store_true',
            'help': 'Terminate running instances.'
            }
        },
    'identity-file': {
        'args': ('-i', '--identity-file'),
        'kwargs': {
            'required': True,
            'help': 'The file from which the private SSH key is read.'
            }
        },
    'package': {
        'args': ('-p', '--package'),
        'kwargs': {
            'required': True,
            'help': 'Path to the backend package to deploy.'
            }
        }
    }

start_args = ('yes-all', 'ec2-region', 'vpc-id', 'subnet-id', 'security-group-id',
              'num-instances', 'ssh-keyname', 'spot-price', 'instance-type',
              'open-public-port', 'commit')
add_args = ('ec2-region', 'vpc-id', 'subnet-id', 'security-group-id', 'num-instances',
            'spot-price')
list_args = ('ec2-region', 'vpc-id', 'subnet-id', 'security-group-id')
command_args = ('ec2-region', 'vpc-id', 'subnet-id', 'security-group-id', 'identity-file')
stop_args = ('ec2-region', 'vpc-id', 'subnet-id', 'security-group-id',
             'terminate')
deploy_args = ('ec2-region', 'vpc-id', 'subnet-id', 'security-group-id',
               'identity-file', 'package')



def add_arguments(parser, arg_names):
    for name in arg_names:
        arg = all_arguments[name]
        parser.add_argument(*arg['args'], **arg['kwargs'])


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    restart_all_parser = subparsers.add_parser('restart',
                                          help='Reboot all ufora_manager and ufora_worker processes')
    restart_all_parser.set_defaults(func=restart_instances)
    add_arguments(restart_all_parser, command_args)

    launch_parser = subparsers.add_parser('start',
                                          help='Launch one or more backend instances')
    launch_parser.set_defaults(func=start_instances)
    add_arguments(launch_parser, start_args)

    add_parser = subparsers.add_parser('add',
                                       help='Add workers to the existing cluster')
    add_parser.set_defaults(func=add_instances)
    add_arguments(add_parser, add_args)

    list_parser = subparsers.add_parser('list',
                                        help='List running backend instances')
    list_parser.set_defaults(func=list_instances)
    add_arguments(list_parser, list_args)

    stop_parser = subparsers.add_parser('stop',
                                        help='Stop all backend instances')
    stop_parser.set_defaults(func=stop_instances)
    add_arguments(stop_parser, stop_args)

    deploy_parser = subparsers.add_parser('deploy',
                                          help='deploy a build to all backend instances')
    deploy_parser.set_defaults(func=deploy_package)
    add_arguments(deploy_parser, deploy_args)

    args = parser.parse_args()
    return args.func(args)
