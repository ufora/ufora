import collections
import itertools

from pyfora.aws.Launcher import Launcher



def enum_(*keys):
    enums = dict(zip(keys, range(len(keys))))
    return type('Enum', (), enums)


_EventTypes = enum_('Launching',
                    'Launched',
                    'LaunchFailed',
                    'InstanceStatus',
                    'WaitingForServices',
                    'Done',
                    'Failed')
class EventTypes(_EventTypes):
    """An enumeration of the types of events that can be emitted during
       calls to :class:`Cluster` methods.

       Attributes:
           Launching: One or more instances are about to be launched.

           Launched: One or more instances have been launched.

           LaunchFailed: One or more instances failed to launch.

           InstanceStatus: An event with detailed progress information.

           WaitingForServices: Starting to wait for all post-launch steps to
               complete and for the pyfora service to start.

           Done: Operation completed successfully.

           Failed: Operation failed.
    """


_ClusterEvent = collections.namedtuple('ClusterEvent', 'event_type body')
class ClusterEvent(_ClusterEvent):
    """An object representing an event emitted during calls to :class:`Cluster` methods.

       Attributes:
           event_type (:class:`EventTypes`): The type of event.
           body: The content of the event, which varies by event type:

            :obj:`EventTypes.Launching`,
            :obj:`EventTypes.LaunchFailed`:
                    Either "manager" or "worker"


            :obj:`EventTypes.WaitingForServices`,
            :obj:`EventTypes.Done`,
            :obj:`EventTypes.Failed`:
                    :obj:`None`


            :obj:`EventTypes.Launched`:
                    A :obj:`tuple` with two elements. The first is a string whose value
                    is either "manager" or "worker", and the second is a list of
                    :class:`boto.ec2.instance` objects.


            :obj:`EventTypes.InstanceStatus`:
                    a :obj:`dict` whose keys are strings that identify various statuses
                    an instances can be in (e.g. 'pending', 'ready', 'installing dependencies',
                    etc.), and the values are lists of :class:`boto.ec2.instance` objects
                    representing all the instances that are in that state.
    """



_Instances = collections.namedtuple('Instances', 'manager workers unfulfilled')
class Instances(_Instances):
    """Collection of instances in a cluster.

       Attributes:
           manager (:obj:`list`): a list (normally of length 1) of :class:`boto.ec2.instance`
               object(s) representing the EC2 instance running the cluster's manager.

           workers (:obj:`list`): a list (possibly empty) of :class:`boto.ec2.instance`
               objects representing the EC2 instances running the cluster's workers.
               Note: The worker running on the manager instances is not included in
               this list.

           unfulfilled (:obj:`list`): a list of zero or more :class:`boto.ec2.SpotInstanceRequest`
               objects representing spot instance requests that have not been fulfilled
               due to price or availability.
    """


class Cluster(object):
    """A cluster of pyfora instances in Amazon Web Services EC2.

    A :class:`~Cluster` object can be used to launch clusters, list instances in a cluster,
    add instances to an existing cluster, or shut down running clusters.

    Args:
        name (str): A name to identify the cluster

        region (str): An AWS region for the cluster (e.g. us-west-2, ap-southeast-1).
            Defaults to 'us-east-1'.
    """
    def __init__(self, name, region):
        self.name = name
        self.region = region


    def list_instances(self):
        """Returns the current instances in the cluster.

        Returns:
            :class:`Instances`: The collection of instances in the cluster.
        """
        launcher = Launcher(self.name, self.region)
        reservations = launcher.get_reservations()
        instances = self._running_or_pending_instances(reservations)
        return Instances(
            manager=[i for i in instances if self._is_manager(i)],
            workers=[i for i in instances if not self._is_manager(i)],
            unfulfilled=reservations['unfulfilled_spot_requests']
            )


    def launch(self,
               instance_type,
               ssh_keyname,
               num_instances=1,
               open_public_port=False,
               vpc_id=None,
               subnet_id=None,
               security_group_id=None,
               spot_price=None,
               callback=None):
        """
        Launches a new cluster in EC2.

        Instances are launched from a vanilla Ubuntu image, docker and other
        dependencies are installed, and the ufora/service image is pulled and started.

        If launching a single instance, it is configured to run both the pyfora mangaer
        and worker. Additional instances only run the worker and are configured to connect
        to the cluster's manager.

        Args:
            instance_type (:obj:`str`): The EC2 instance type to use (e.g. c3.4xlarge, m4.large, etc.)

            ssh_keyname (:obj:`str`): The name of an SSH key-pair in EC2. Instances are launched
                with that key and you MUST have its private key in order to SSH into
                them.

            num_instances (:obj:`int`, optional): The number of instances to launch. Defaults to 1.

            open_public_port (:obj:`bool`, optional): Whether the pyfora HTTP port should be
                open for access over the internet. Defaults to False.
                If False, you can only connect to the cluster from with EC2 or by tunnelling
                HTTP over SSH.

            vpc_id (:obj:`str`, optional): The id of an EC2 Virtual Private Cloud (VPC) into which the
                instances are launched. Attempt to launch to EC2 Classic if omitted.

            subnet_id (:obj:`str`, optional): If using vpc_id, this is the ID of the VPC
                subnet to launch the instances into.

            security_group_id (:obj:`str`, optional): The ID of an EC2 Security Group to launch
                the instances into. If omitted, a new security group called "pyfora" is
                created.

            spot_price (:obj:`float`, optional): If specified, launch the cluster using
                EC2 spot instances with the specified max bid price.

            callback (:obj:`callable`, optional): An optional callback that receives progress
                notifications during the launch process. The callable should accept a single
                argument of type :class:`ClusterEvent`.

        Returns:
            :class:`Instances`: The collection of instances in the newly created cluster.
        """
        callback = self._trigger_event(callback or (lambda x: None))
        launcher = Launcher(self.name,
                            self.region,
                            vpc_id,
                            subnet_id,
                            security_group_id,
                            instance_type,
                            open_public_port)

        callback(EventTypes.Launching, 'manager')

        manager = launcher.launch_manager(ssh_keyname,
                                          spot_price,
                                          self._instance_status(callback))
        if not manager:
            callback(EventTypes.LaunchFailed, 'manager')
            return None

        callback(EventTypes.Launched, ('manager', [manager]))

        workers = []
        if num_instances > 1:
            callback(EventTypes.Launching, 'worker')
            workers = self._launch_workers(
                launcher,
                num_instances - 1,
                ssh_keyname,
                manager.id,
                spot_price,
                callback=callback
                )

        self._wait_for_services(launcher, [manager] + workers, callback=callback)
        return self.list_instances()


    def add_workers(self, manager, num_workers, spot_price=None, callback=None):
        """Adds workers to an existing cluster.

        The EC2 instance type used launch the added workers is the same as that
        of the already launched instances.

        Args:
            manager (:class:`boto.ec2.instance`): The cluster's manager.
                It can be retrieved by calling :func:`Cluster.list_instances`.

            num_workers (:obj:`int`): The number of workers to add.

            spot_price (:obj:`float`, optional): If specified, launch the cluster using
                EC2 spot instances with the specified max bid price.

            callback (:obj:`callable`, optional): An optional callback that receives progress
                notifications during the launch process. The callable should accept a single
                argument of type :class:`ClusterEvent`.


        Returns (list):
            A list of :class:`boto.ec2.instance` objects representing the launched workers.
        """
        callback = self._trigger_event(callback or (lambda x: None))
        launcher = Launcher(self.name,
                            self.region,
                            manager.vpc_id,
                            manager.subnet_id,
                            manager.groups[0].id,
                            manager.instance_type)

        callback(EventTypes.Launching, 'worker')

        workers = self._launch_workers(launcher,
                                       num_workers,
                                       manager.key_name,
                                       manager.id,
                                       spot_price,
                                       callback=callback)
        if not workers:
            callback(EventTypes.Failed, None)
        else:
            self._wait_for_services(launcher,
                                    workers,
                                    callback=callback)
        return workers


    def stop(self, instances=None, terminate=False):
        """Stops or terminates instances.

        Args:
            instances (:obj:`list`, optional): a list of :class:`boto.ec2.instance`
                objects representing the instances to be stopped. If omitted, all
                instances in the cluster are stopped.

            terminate (:obj:`bool`, optional): If True, instances are terminated.
                Otherwise they are stopped. On clusters of spot instances, this
                argument must be set to True because spot instances cannot be stopped,
                only terminated.
        """
        instances = instances or self.list_instances()
        for i in itertools.chain(instances.workers, instances.manager):
            if terminate:
                i.terminate()
            else:
                i.stop()

        for r in instances.unfulfilled:
            r.cancel()

        return instances


    @classmethod
    def _launch_workers(cls, launcher, count, ssh_keyname, manager_id, spot_price, callback):
        workers = launcher.launch_workers(count,
                                          ssh_keyname,
                                          manager_id,
                                          spot_price,
                                          cls._instance_status(callback))
        if not workers:
            callback(EventTypes.LaunchFailed, 'worker')
        else:
            callback(EventTypes.Launched, ('worker', workers))
        return workers


    @classmethod
    def _wait_for_services(cls, launcher, instances, callback):
        callback(EventTypes.WaitingForServices, None)
        if launcher.wait_for_services(instances, callback=cls._instance_status(callback)):
            callback(EventTypes.Done, None)
        else:
            callback(EventTypes.Failed, None)


    @staticmethod
    def _instance_status(callback):
        def f(s):
            callback(EventTypes.InstanceStatus, s)
        return f


    @staticmethod
    def _trigger_event(callback):
        def f(event_type, body):
            callback(ClusterEvent(event_type, body))
        return f


    @classmethod
    def _running_or_pending_instances(cls, reservations):
        return cls._instances_in_state(reservations, ('running', 'pending'))


    @staticmethod
    def _instances_in_state(reservations, states):
        return [i for i in reservations['instances'] if i.state in states]


    @staticmethod
    def _is_manager(instance):
        return 'Name' in instance.tags and 'manager' in instance.tags['Name']


