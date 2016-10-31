import argparse
import itertools
import os
import subprocess
import sys
import threading
import time
from pyfora.aws.Cluster import Cluster, EventTypes


def get_region(region):
    region = region or os.getenv('PYFORA_AWS_EC2_REGION')
    if region is None:
        raise ValueError('EC2 region not specified')
    return region

def get_ssh_keyname(keyname):
    return keyname or os.getenv('PYFORA_AWS_SSH_KEYNAME')

def get_identity_file(filename):
    return filename or os.getenv('PYFORA_AWS_IDENTITY_FILE')

class StatusPrinter(object):
    spinner = ['|', '/', '-', '\\']

    def __init__(self, open_public_port=False):
        self.open_public_port = open_public_port
        self.spinner_index = 0
        self.last_message_len = 0
        self.last_message = ""


    def on_event(self, event):
        if event.event_type == EventTypes.Launching:
            if event.body == 'manager':
                print "Launching manager instance:"
            else:
                print "Launching worker instance(s):"

        elif event.event_type == EventTypes.InstanceStatus:
            self.on_status(event.body)

        elif event.event_type == EventTypes.LaunchFailed:
            self.failed()
            if event.body == 'worker':
                print "Worker(s) could not be launched."

        elif event.event_type == EventTypes.Launched:
            instance_type, instances = event.body
            if instance_type == 'manager':
                instance = instances[0]
                print "Manager instance started:\n"
                print_instance(instance, instance_type)
                print
                if not self.open_public_port:
                    print "To tunnel the pyfora HTTP port (30000) over ssh, run the following command:"
                    print "    ssh -i <ssh_key_file> -L 30000:localhost:30000 ubuntu@%s\n" % instance.ip_address
            else:
                self.done()
                print "Worker instance(s) started:"
                for worker in instances:
                    print_instance(worker, 'worker')

        elif event.event_type == EventTypes.WaitingForServices:
            print "Waiting for services:"

        elif event.event_type == EventTypes.Done:
            self.done()

        elif event.event_type == EventTypes.Failed:
            self.failed()

        else:
            print "Unexpected status event:", event.event_type



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
    if not parsed_args.name:
        print "You did not specify a cluster name (--name). Using default name 'pyfora'."
        parsed_args.name = 'pyfora'

    return {
        'name': parsed_args.name,
        'region': get_region(parsed_args.ec2_region)
        }


def worker_logs(args):
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()
    instances = instances.manager + instances.workers
    identity_file = get_identity_file(args.identity_file)

    def grep(instance):
        #note that we have to swap "A" and "B" because tac has reversed the order of the lines.
        command = ('"source ufora_setup.sh; tac \\$LOG_DIR/logs/ufora-worker.log '
                   '| grep -m %s -B %s -A %s -e %s" | tac') % (args.N,
                                                               args.A,
                                                               args.B,
                                                               args.expression)

        return (pad(instance.ip_address + "> ", 25),
                ssh_output(identity_file, instance.ip_address, command))

    for ip, res in parallel_for(instances, grep):
        for line in res.split("\n"):
            print ip, line


def worker_load(args):
    cmd_to_run = 'tail -f /mnt/ufora/logs/ufora-worker.log' if args.logs else \
        'sudo apt-get install htop\\; htop'
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()
    instances = instances.manager + instances.workers
    identity_file = get_identity_file(args.identity_file)

    session = os.getenv("USER")
    def sh(cmd, **kwargs):
        try:
            print "CMD =", cmd.format(SESSION=session, **kwargs)
            subprocess.check_output(cmd.format(SESSION=session, **kwargs), shell=True)
        except subprocess.CalledProcessError:
            import traceback
            traceback.print_exc()

    sh("tmux -2 kill-session -t {SESSION}")

    sh("tmux -2 new-session -d -s {SESSION}")

    # Setup a window for tailing log files
    sh("tmux new-window -t {SESSION}:1 -n 'pyfora_htop'")

    for ix in xrange((len(instances)-1)/2):
        sh("tmux split-window -v -t 0 -l 20")

    for ix in xrange(len(instances)/2):
        sh("tmux split-window -h -t {ix}", ix=ix)

    # for ix in xrange(len(instances)-1,0,-1):
    #     sh('tmux resize-pane -t {ix} -y 20', ix=ix)

    for ix in xrange(len(instances)):
        sh('tmux send-keys -t {ix} "ssh ubuntu@%s -t -i %s %s" C-m' % (instances[ix].ip_address,
                                                                       identity_file,
                                                                       cmd_to_run),
           ix=ix)


    # Attach to session
    sh('tmux -2 attach-session -t {SESSION}')



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

    if args.name is None:
        args.name = 'pyfora'
        print '--name argument was not specified. Using default name: ' + args.name

    status_printer = StatusPrinter(args.open_public_port)

    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.launch(args.instance_type,
                               ssh_keyname,
                               args.num_instances,
                               open_public_port,
                               args.vpc_id,
                               args.subnet_id,
                               args.security_group_id,
                               args.spot_price,
                               status_printer.on_event)


    if not instances.manager:
        list_instances(args)
        return


def pad(s, ct):
    return s + " " * max(ct - len(s), 0)

def restart_instances(args):
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()
    instances = instances.manager + instances.workers
    identity_file = get_identity_file(args.identity_file)

    def restart_instance(instance):
        is_manager = 'manager' in instance.tags.get('Name', '')

        if is_manager:
            command = ('"source ufora_setup.sh; \\$DOCKER stop ufora_manager; '
                       'sudo rm -rf \\$LOG_DIR/*; \\$DOCKER start ufora_manager"')
        else:
            command = ('"source ufora_setup.sh; \\$DOCKER stop ufora_worker; '
                       'sudo rm -rf \\$LOG_DIR/*; \\$DOCKER start ufora_worker"')

        return (pad(instance.ip_address + "> ", 25),
                ssh_output(identity_file, instance.ip_address, command))

    for ip, res in parallel_for(instances, restart_instance):
        for line in res.split("\n"):
            print ip, line



def add_instances(args):
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()

    if len(instances.manager) > 1:
        print "There is more than one Manager instance. Can't add workers.", \
            "Managers:"
        for m in instances.manager:
            print_instance(m)
        return 1
    elif len(instances.manager) == 0:
        print "No manager instance is running. Can't add workers."
        return 1

    if args.num_instances < 1:
        print "--num-instances must be greater or equal to 1."
        return 1

    status_printer = StatusPrinter()
    cluster.add_workers(instances.manager[0],
                        args.num_instances,
                        args.spot_price,
                        status_printer.on_event)


    status_printer.done()


def list_instances(args):
    cluster = Cluster(args.name, get_region(args.ec2_region))
    instances = cluster.list_instances()
    count = len(instances.workers)
    if instances.manager:
        count += len(instances.manager)
        if len(instances.manager) > 1:
            print "Something is wrong! This cluster has more than one manager!"

    print "%d instance%s%s" % (count, 's' if count != 1 else '', ':' if count > 0 else '')
    for manager in instances.manager:
        print_instance(manager)
    for i in instances.workers:
        print_instance(i)

    if instances.unfulfilled:
        print ""
        count = len(instances.unfulfilled)
        print "%d unfulfilled spot instance request%s:" % (count, 's' if count != 1 else '')
        for r in instances.unfulfilled:
            print_spot_request(r)


def stop_instances(args):
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()

    count = len(instances.manager) + len(instances.workers)
    if count == 0:
        print "No running instances to stop"
    else:
        verb = 'Terminating' if args.terminate else 'Stopping'
        print '%s %d instances:' % (verb, count)
        for i in itertools.chain(instances.workers, instances.manager):
            print_instance(i)

    if instances.unfulfilled:
        print "Cancelling %d unfulfilled spot instance requests:" % len(instances.unfulfilled)
        for r in instances.unfulfilled:
            print_spot_request(r)

    cluster.stop(instances, args.terminate)


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
    cluster = Cluster(args.name, args.ec2_region)
    instances = cluster.list_instances()
    instances = instances.manager + instances.workers
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
    results = upload_package(args.package, instances, get_identity_file(args.identity_file))
    if any_failures(results):
        print "Failed to upload package:"
        print_failures(results)
        return
    print "Package uploaded successfully"
    print ''

    print "Updating service..."
    results = update_ufora_service(instances, get_identity_file(args.identity_file))
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
    return [i for i in reservations['instances'] if i.state in states]


def print_instance(instance, tag=None):
    output = "    %s | %s | %s" % (instance.id, instance.ip_address, instance.state)
    if tag is None and 'Name' in instance.tags:
        tag = 'manager' if 'manager' in instance.tags['Name'] else 'worker'

    tag = tag or ''
    if tag:
        output += " | " + tag
    print output


def print_spot_request(request):
    print "    %s | %s | %s" % (request.id, request.state, request.status.code)


all_arguments = {
    'yes-all': {
        'args': ('-y', '--yes-all'),
        'kwargs': {
            'action': 'store_true',
            'help': 'Do not prompt user input. Answer "yes" to all prompts.'
            }
        },
    'name': {
        'args': ('--name',),
        'kwargs': {
            'help': 'The name of the cluster. Default: "pyfora"'
            }
        },
    'ec2-region': {
        'args': ('--ec2-region',),
        'kwargs': {
            'default':  os.getenv('PYFORA_AWS_EC2_REGION') or 'us-east-1',
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
    'identity-file': {
        'args': ('-i', '--identity-file'),
        'kwargs': {
            'required': os.getenv('PYFORA_AWS_IDENTITY_FILE') is None,
            'default': os.getenv('PYFORA_AWS_IDENTITY_FILE'),
            'help': 'The file from which the private SSH key is read. '
                    'Can also be set using the PYFORA_AWS_IDENTITY_FILE environment variable.'
            }
        }
    }

common_args = ('name', 'ec2-region')
launch_args = common_args + ('num-instances', 'spot-price')
start_args = launch_args + ('yes-all', 'vpc-id', 'subnet-id', 'security-group-id',
                            'ssh-keyname', 'instance-type', 'open-public-port', 'commit')
add_args = launch_args
list_args = common_args
command_args = common_args + ('identity-file',)



def add_arguments(parser, arg_names):
    for name in arg_names:
        arg = all_arguments[name]
        parser.add_argument(*arg['args'], **arg['kwargs'])


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    restart_all_parser = subparsers.add_parser(
        'restart',
        help='Reboot all ufora_manager and ufora_worker processes'
        )
    restart_all_parser.set_defaults(func=restart_instances)
    add_arguments(restart_all_parser, command_args)


    worker_logs_parser = subparsers.add_parser(
        'worker_logs',
        help='Return the last N lines of logs matching a particular regex')
    worker_logs_parser.set_defaults(func=worker_logs)
    add_arguments(worker_logs_parser, command_args)
    worker_logs_parser.add_argument('N', type=int, default=1, help="Number of matches to return")
    worker_logs_parser.add_argument('-e',
                                    '--expression',
                                    type=str,
                                    required=True,
                                    help="Regular expression to search for")
    worker_logs_parser.add_argument('-A',
                                    type=int,
                                    required=False,
                                    default=0,
                                    help="Lines of context after the expression")
    worker_logs_parser.add_argument('-B',
                                    type=int,
                                    required=False,
                                    default=0,
                                    help="Lines of context before the expression")


    worker_load_parser = subparsers.add_parser('worker_load',
                                               help='Run htop in tmux for all workers')
    worker_load_parser.set_defaults(func=worker_load)
    worker_load_parser.add_argument('-l',
                                    '--logs',
                                    action='store_true',
                                    default=False,
                                    help="Instead of htop, tail the logs")
    add_arguments(worker_load_parser, command_args)


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
    add_arguments(stop_parser, common_args)
    stop_parser.add_argument('--terminate',
                             action='store_true',
                             help=('Terminate instances instead of stopping them. '
                                   'Spot instances cannot be stopped, only terminated.'))


    deploy_parser = subparsers.add_parser('deploy',
                                          help='deploy a build to all backend instances')
    deploy_parser.set_defaults(func=deploy_package)
    add_arguments(deploy_parser, command_args)
    deploy_parser.add_argument('-p', '--package', required=True,
                               help='Path to the backend pagacke to deploy.')

    args = parser.parse_args()
    return args.func(args)
