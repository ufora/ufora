app = angular.module('pyfora', ['btford.socket-io'])

app.factory 'socketIo', (socketFactory) ->
    ioSocket = io.connect('/subscribableWebObjects')
    socket = socketFactory({ioSocket: ioSocket})

    promise = new Promise (resolve, reject) ->
        socket.on 'connect', () ->
            socket.emit 'handshake', {version: pyfora_version}

        socket.on 'handshake', (resp) ->
            if resp is 'ok'
                resolve(socket)
            else
                reject(Error("Failed to connect: #{resp}"))
    promise




app.controller 'DashboardController', ($scope, subscribableObjects) ->
    $scope.message = "Version: #{pyfora_version}"

    subscribableObjects.then (so) ->
        pyfora_cluster = so.getInterfaceInstance('PyforaCluster', {})
        pyfora_cluster._raw.getClusterStatus {},
            onSuccess: (status) ->
                $scope.cluster_status = status
                $scope.$apply()
            onFailure: (err) ->
                console.error("Error: #{err}")
                $scope.cluster_status = err
                $scope.$apply()









