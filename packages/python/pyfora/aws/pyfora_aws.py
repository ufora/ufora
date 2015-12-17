import argparse
import os
from pyfora.aws.Launcher import Launcher

def get_region(region):
    region = region or os.getenv('PYFORA_AWS_EC2_REGION')
    if region is None:
        raise ValueError('EC2 region not specified')
    return region


def get_ssh_keyname(keyname):
    return keyname or os.getenv('PYFORA_AWS_SSH_KEYNAME')


def start_instances(args):
    assert args.num_instances > 0
    ssh_keyname = get_ssh_keyname(args.ssh_keyname)
    open_public_port = args.open_public_port or ssh_keyname is None

    launcher = Launcher(region=get_region(args.ec2_region),
                        vpc_id=args.vpc_id,
                        subnet_id=args.subnet_id,
                        security_group_id=args.security_group_id,
                        instance_type=args.instance_type,
                        open_public_port=open_public_port)
    print "Launching ufora manager..."
    manager = launcher.launch_manager(ssh_keyname, args.spot_price)
    print "Ufora manager started:\n"
    print_instance(manager, 'manager')
    print ""
    if not args.open_public_port:
        print "To tunnel Ufora's HTTP port (30000) over ssh, run the following command:"
        print "    ssh -i <ssh_key_file> -L 30000:localhost:30000 ubuntu@%s\n" % manager.ip_address

    workers = []
    if args.num_instances > 1:
        print "Launching workers..."
        workers = launcher.launch_workers(args.num_instances-1,
                                          ssh_keyname,
                                          manager.id,
                                          args.spot_price)
        print "Workers started:"
    for worker in workers:
        print_instance(worker, 'worker')


def add_instances(args):
    launcher = Launcher(region=get_region(args.ec2_region))
    manager = [i for i in running_or_pending_instances(launcher.get_reservations())
               if 'Name' in i.tags and i.tags['Name'].startswith('ufora manager')]
    if len(manager) > 1:
        print "There is more than one Ufora Manager instance. Can't add workers.", \
            "Managers:"
        for m in manager:
            print_instance(m)
        return 1
    elif len(manager) == 0:
        print "No Ufora Manager instances are running. Can't add workers."
        return 1

    if args.num_instances < 1:
        print "--num-instances must be greater or equal to 1."
        return 1

    manager = manager[0]
    launcher.vpc_id = manager.vpc_id
    launcher.subnet_id = manager.subnet_id
    launcher.instance_type = manager.instance_type
    launcher.security_group_id = manager.groups[0].id

    print "Launching workers..."
    workers = launcher.launch_workers(args.num_instances,
                                      manager.key_name,
                                      manager.id,
                                      args.spot_price)
    print "Workers started:"
    for worker in workers:
        print_instance(worker, 'worker')


def list_instances(args):
    launcher = Launcher(region=get_region(args.ec2_region))
    reservations = launcher.get_reservations()
    count = sum(len(r.instances) for r in reservations)
    print "%d instance%s%s" % (
        count, 's' if count != 1 else '', ':' if count > 0 else ''
        )
    for r in reservations:
        for i in r.instances:
            print_instance(i)


def stop_instances(args):
    launcher = Launcher(region=get_region(args.ec2_region))
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


def running_or_pending_instances(reservations):
    return [
        i for r in reservations
        for i in r.instances
        if i.state == 'running' or i.state == 'pending'
        ]


def print_instance(instance, tag=None):
    output = "    %s | %s | %s" % (instance.id, instance.ip_address, instance.state)
    if tag is None and 'Name' in instance.tags:
        tag = 'manager' if instance.tags['Name'].startswith('ufora manager') else 'worker'

    tag = tag or ''
    if tag:
        output += " | " + tag
    print output

all_arguments = {
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
            'help': ('The id of the VPC to launch instances into. '
                     'EC2 Classic is used if this argument is omitted.')
            }
        },
    'subnet-id': {
        'args': ('--subnet-id',),
        'kwargs': {
            'help': ('The id of the VPC subnet to launch instances into. '
                     'This argument must be specified if --vpc-id is used and is '
                     'ignored otherwise.')
            }
        },
    'security-group-id': {
        'args': ('--security-group-id',),
        'kwargs': {
            'help': ('The id of the EC2 security group to launch instances into. '
                     'If omitted, a security group called "ufora" will be created and used.')
            }
        },
    'open-public-port': {
        'args': ('--open-public-port',),
        'kwargs': {
            'action': 'store_true',
            'help': ('If specified, HTTP access to the manager machine will be open from '
                     'anywhere (0.0.0.0/0). Use with care! '
                     'Anyone will be able to connect to your cluster. '
                     "As an alternative, considering tunneling Ufora's HTTP port (30000) "
                     'over SSH using the -L argument.')
            }
        },
    'terminate': {
        'args': ('--terminate',),
        'kwargs': {
            'action': 'store_true',
            'help': 'Terminate running instances.'
            }
        }
    }

start_args = ('ec2-region', 'num-instances', 'ssh-keyname', 'spot-price',
              'instance-type', 'vpc-id', 'subnet-id', 'security-group-id',
              'open-public-port')
add_args = ('ec2-region', 'num-instances', 'spot-price')
list_args = ('ec2-region',)
stop_args = ('ec2-region', 'terminate')


def add_arguments(parser, arg_names):
    for name in arg_names:
        arg = all_arguments[name]
        parser.add_argument(*arg['args'], **arg['kwargs'])


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    launch_parser = subparsers.add_parser('start',
                                          help='Launch ufora instances')
    launch_parser.set_defaults(func=start_instances)
    add_arguments(launch_parser, start_args)

    add_parser = subparsers.add_parser('add',
                                       help='Add workers to the existing cluster')
    add_parser.set_defaults(func=add_instances)
    add_arguments(add_parser, add_args)

    list_parser = subparsers.add_parser('list',
                                        help='List running ufora instances')
    list_parser.set_defaults(func=list_instances)
    add_arguments(list_parser, list_args)

    stop_parser = subparsers.add_parser('stop',
                                        help='Stop all ufora instances')
    stop_parser.set_defaults(func=stop_instances)
    add_arguments(stop_parser, stop_args)

    args = parser.parse_args()
    return args.func(args)
