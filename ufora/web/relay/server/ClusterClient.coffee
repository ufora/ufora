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

fs = require('fs')
net = require('net')

logger = require('./logging')

messageReader = require('./MessageReader')

clusterManagerCert = null
clusterManagerIpEndpoint = null

module.exports.initialize = (options) ->
    clusterManagerIpEndpoint = {host: options.host, port: options.port}
    clusterManagerCert = fs.readFileSync(options.ca) if options.ca?

module.exports.getEndpoint = ->
    return clusterManagerIpEndpoint

connect = (port, host) ->
    options =
        rejectUnauthorized: true
    options.ca = [clusterManagerCert] if clusterManagerCert?

    return net.connect port, host, =>

module.exports.connect = connect

module.exports.getBackendIpEndpoint = (callback) ->
    socket = connect(clusterManagerIpEndpoint.port, clusterManagerIpEndpoint.host)
    socket.on 'connect', =>
        clusterStatusRequest =
            message_type: 'ClusterStatusRequest'
            message_data: JSON.stringify({
                clusterName: 'Backend',
                includeInvalid: false
                })
            credentials: JSON.stringify({
                username: '',
                password: ''
                })
        messageReader.sendData(socket, new Buffer(JSON.stringify(clusterStatusRequest)))

        reader = messageReader.create (buffer) =>
            # This is some gnarly deserialization logic.
            # We really need to change how we (de)serialize objects in cluster manager
            try
                clusterStatus = JSON.parse(JSON.parse(buffer.toString())[1])

                if not clusterStatus.assignmentStatuses? or not clusterStatus.assignmentStatuses.length?
                    logger.error "Illegal response from cluster manager: #{buffer.toString()}"
                    callback('Illegal response from clusterManager', null)
                else if clusterStatus.assignmentStatuses.length > 0
                    for serializedAssignment in clusterStatus.assignmentStatuses
                        assignment = JSON.parse(serializedAssignment)
                        if /BackendGatewayService/.test(assignment.role)
                            machine = JSON.parse(assignment.machineStatusTuple[0][0])
                            if machine.machine_type == 'ec2'
                                callback(null, {host: JSON.parse(machine.state).privateIp, port:null})
                                return
                            else if machine.machine_type == 'local'
                                callback(null, {host: machine.privateIp, port:null})
                                return
                callback('No SharedState assignment found', null)
            catch error
                logger.error "Exception trying to parse cluster manager response: #{error}"
                for line in error.stack.split('\n')
                    logger.error line
                callback('Illegal response from clusterManager', null)
            socket.end()



        socket.on 'data', (data) =>
            reader.addData(data)

    socket.on 'error', (error) =>
        callback(error, null)

