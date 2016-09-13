import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph

class PyforaCluster(ComputedGraph.Location):
    @ComputedGraph.ExposedFunction()
    def getClusterStatus(self, args):
        gateway = ComputedValueGateway.getGateway().cumulusGateway
        status = gateway.getClusterStatus()
        return status
