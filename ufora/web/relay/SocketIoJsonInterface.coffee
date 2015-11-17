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

if module?
  Logger = require './logging.coffee'
  logging = new Logger
    logging_levels:
      debug: true
      info: true
      log: true
      warn: true
      error: true

class SocketIoJsonInterface
    constructor: (@io, @version) ->
        @messageId = 0
        @socket = null
        @pendingCallbacks = {}
        @onUnknownMessage = null

    disconnect: () =>
        if @socket
            @socket.removeAllListeners()
            @socket = null

    connect: (args) =>
        """Connect to a remote interface. args should contain
            socket - a socket.io socket
            onDisconnected(msg) ->
            onError(msg) ->
            onConnected() ->
        """
        @socket = socket = @io.connect(args.url, {multiplex: false})

        # Socket.IO built-in events
        socket.on 'connect', =>
            logging.info "Socket connect"

            socket.emit 'handshake', {version: @version}
            socket.on 'handshake', (handshake_response) =>
                logging.info "Handshake response:", handshake_response
                unless handshake_response is 'ok'
                    return args.onDisconnected("Error: #{handshake_response}")

                args.onConnected()
                # Message handlers
                socket.on 'response', @handleMessageFromServer

        socket.on 'error', (data) =>
            logging.info "Socket error"
            args.onDisconnected("Error: #{data}")
            socket.disconnect()

        socket.on 'disconnect', =>
            logging.info "Socket disconnect"
            args.onDisconnected 'Socket disconnected'

            attemptReconnect = () =>
                logging.info "Attempting to reconnect..."
                if args.reconnectFunc?
                  args.reconnectFunc()

            if not @reconnecter?
                @reconnecter = setTimeout(attemptReconnect, 2000)

        socket.on 'reconnect', (attemptCount) =>
            #need a logging model here
            logging.info "Socket reconnected successfully. Attempt:", attemptCount
            return

        socket.on 'reconnecting', () ->
            logging.info "Socket.io attempting to reconnect..."

        socket.on 'reconnect_error', (err) ->
            logging.log "Socket reconnect error:", err

        socket.on 'reconnect_failed', ->
            logging.log "Socket reconnect failed."


    handleMessageFromServer: (data) =>
        data = JSON.parse(data)

        if not data.messageId?
            #need a logging model here
            if @onUnknownMessage?
                @onUnknownMessage(data)
            return

        callback = @pendingCallbacks[data.messageId]
        if not callback?
            if @onUnknownMessage?
                @onUnknownMessage(data)
            return

        if data.responseType != 'SubscribeResponse'
            delete @pendingCallbacks[data.messageId]

        return callback(data)

    request: (data, callback) =>
        messageId = @messageId
        @messageId += 1

        @pendingCallbacks[messageId] = callback

        data.messageId = messageId

        @socket.emit 'message', {body: JSON.stringify(data)}

module.exports = SocketIoJsonInterface if module?

