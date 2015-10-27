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

chai = require '../../ufora/web/relay/node_modules/chai'
should = chai.should()

async = require '../../ufora/web/relay/node_modules/async'

relayCoffeePath = "../../ufora/web/relay/"
subscribableClassesPath = "../../ufora/BackendGateway/SubscribableWebObjects/ObjectClassesToExpose/"

SocketIoJsonInterface = require(relayCoffeePath + "SocketIoJsonInterface")
SubscribableWebObjects = require(relayCoffeePath + "SubscribableWebObjects")

TestTest = require(subscribableClassesPath + "Test.test")

io = require('../../ufora/web/relay/node_modules/socket.io/node_modules/socket.io-client')

# nodejs doesn't like self-signed certs. This is a workaround for local testing
require('https').globalAgent.options.rejectUnauthorized = false

connect = (callback) ->
    socketInterface = new SocketIoJsonInterface()

    socket = io.connect "http://localhost:30000/subscribableWebObjects",
        multiplex: false

    console.info "connection socket.io."
    socketInterface.connect
        socket: socket
        onConnected: ()->
            callback(null, socketInterface)
        onError: (msg)->
            callback(new Error(msg))
        onDisconnected: (reason)->
            console.error "socket.io disconnected. #{reason}"

describe "BackendGatewayLoadTest", ->
    describe 'ConnectRepeatedly', ->
        #give the test 5 minutes
        @timeout 300000

        it 'should allow us to connect many times in many threads', (done)->
            threadsFinished = 0
            totalThreads = 10

            tryToIncrement = (index, incrementBy, maxValueToHit)->
                console.log "Connection attempt #{index}"

                connect (err, newInterface) ->
                    return done(err) if err?

                    console.log "Connection attempt #{index} succeeded. Testing."

                    if index > maxValueToHit
                        threadsFinished = threadsFinished + 1
                        console.log("Finished thread ending on #{index}")
                        if threadsFinished >= totalThreads
                            done()
                        return

                    webObjects = SubscribableWebObjects(newInterface, maxObjectIds=10)

                    TestCGLocation = webObjects.TestCGLocation
                    testCgLocationObject = new TestCGLocation({definition: index})

                    console.log "Connection attempt #{index} succeeded. Requesting cg location"

                    testCgLocationObject.get_testCgLocation 
                        onSuccess: (value) ->
                            newInterface.socket.disconnect()
                            tryToIncrement(index+incrementBy, incrementBy, maxValueToHit)
                        onFailure: (error) -> done(new Error("failed to get the cg location: #{error}"))

            for i in [0...totalThreads]
                tryToIncrement(i, 10, 100)

describe "SubscribableWebObjects", ->
    @timeout 60000
    socketInterface = null
    webObjects = [null]
    testObject = null

    before (done) ->
        connect (err, newInterface) ->
            return done(err) if err?
            should.exist newInterface

            socketInterface = newInterface
            webObjects[0] = SubscribableWebObjects(socketInterface, maxObjectIds=10)
            should.exist webObjects[0]
            done()

    describe 'Test', ->
        TestTest webObjects

