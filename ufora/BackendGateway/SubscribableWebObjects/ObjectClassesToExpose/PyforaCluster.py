import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import logging

class PyforaCluster(ComputedGraph.Location):
    @ComputedGraph.ExposedFunction()
    def getClusterStatus(self, args):
        logging.info("Called!!")
        gateway = ComputedValueGateway.getGateway().cumulusGateway
        status = gateway.getClusterStatus()
        logging.info("Cluster status: %s", status)
        return status
