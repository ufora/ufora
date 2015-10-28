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

net = require 'net'
uuid = require 'node-uuid'
async = require 'async'

logger = null
messageReader = require './MessageReader'
queue = require './queue'


class Relay
  constructor: (app) ->
    @socketIOSessions = {}
    @app = app
    @logger = app.get 'logger'
    @logger.info 'initializing node socket.io server'

    @gatewayEndpoint =
      host: app.get 'gatewayhost'
      port: app.get 'gatewayport'
    @logger.info 'Gateway Service endpoint:', @gatewayEndpoint


  initializeSocketIO: (server) =>
    io = require('socket.io')(server)

    # create two socket namespaces. connectors must choose which one they want
    ioNS = io.of('/subscribableWebObjects')
    ioNS.on 'connection', (socket) =>
      @registerSubscribableWebObjectsHandlers(socket)

  hasSession: (socket) =>
    socket.id of @socketIOSessions and @socketIOSessions[socket.id].session?

  setSession: (socket, session) =>
    @socketIOSessions[socket.id] = session

  getSession: (socket) =>
    @socketIOSessions[socket.id]

  deleteSession: (socket) =>
    session = @socketIOSessions[socket.id]
    delete @socketIOSessions[socket.id]
    return session

  registerSubscribableWebObjectsHandlers: (socket) =>
    @setSession(socket, {})
    socket.on 'message', (payload) =>
      @logger.info "Received message on subscribable socket:", payload
      unless payload?.body?
        @logger.error('Invalid data in "message": ', payload)
        return socket.disconnect()

      @handleIncomingSubscribableWebObjectsMessage socket,
        content: payload.body

    socket.on 'disconnect', =>
      session =  @deleteSession(socket)
      @logger.info "subscribableWebObjects socket disconnected."
      if session.channel?
        channel = session.channel
        session.channel = null
        channel.onDisconnect('socket.io connection to browser closed')

  handleIncomingSubscribableWebObjectsMessage: (socket, message) =>
    session = @getSession(socket)
    if session.channel?
      @logger.info "pushing message to session channel. socket.id:", socket.id
      @pushMessageToBackend(socket, message)
      return

    @logger.debug "Backend channel has not been established yet. Message:", message
    if session.messagesPendingConnection?
      @logger.debug "Saving pending message:", message
      return session.messagesPendingConnection.push message

    # this is the first messages on this socket.
    # need to connect to backend
    session.messagesPendingConnection = [message]
    @logger.debug "creating channel for message:", message

    channel = @make_channel
      group: "SubscribableWebObjects"
      id: uuid.v4()
      host: @gatewayEndpoint.host
      port: @gatewayEndpoint.port
      encoding: 'utf8'

    channel.onDisconnect = (reason) =>
      @logger.info "SubscribableWebObjects channel disconnected from backend. Reason:", reason
      socket.disconnect()

      if channel.socket?
        backend_socket = channel.socket
        channel.socket = null
        backend_socket.end()

    messageCallback = (buffer) =>
      response = buffer.toString('utf8')
      @logger.info "Emitting response:", response
      socket.emit "response", response

    channel.upstreamMessages = queue.create -1, (messageToSend) =>
      if messageToSend.content.length is 0
        # A zero-length message means that the client is initiating a disconnect
        channel.onDisconnect 'Graceful disconnect initiated by client'
      else if channel.socket?
        @logger.info "sending message to backend:", messageToSend.content
        messageReader.sendData channel.socket,
          new Buffer(messageToSend.content, channel.encodingType)

    channelReadyCallback = () =>
      initialMessage =
        content: JSON.stringify
          requestType: 'SubscribableWebObjects'

      @logger.debug "sending initial message: ", initialMessage
      channel.upstreamMessages.push initialMessage, (err) =>
        if err?
          @logger.error "Failed to send initial message to backend gateway"
          channel.onDisconnect()

      @logger.debug "draining pending messages:", session.messagesPendingConnection
      while session.messagesPendingConnection.length > 0
        msg = session.messagesPendingConnection.shift()
        @logger.debug "Pushing message to backend:", msg
        channel.upstreamMessages.push(msg)
      session.channel = channel

    socketConnector = @createSocketConnector channel
    @connectChannel channel, socketConnector, messageCallback, channelReadyCallback


  pushMessageToBackend: (socket, message) =>
    session = @getSession(socket)
    session.channel.upstreamMessages.push message, (err) ->
      if err?
        @logger.error "Error enqueuing message:", message, "Error:", err
        socket.disconnect()


  make_channel: ({group, id, host, port, encoding}) =>
    channel =
      group: group
      id: id
      host: host
      port: port
      encodingType: encoding
      disconnect: () ->
        @socket?.destroy()

  connectChannel: (channel, socketConnector, messageCallback, channelReadyCallback) =>
    reader = messageReader.create (buffer) ->
      messageCallback(buffer)

    socket = channel.socket = socketConnector.connect channel.port, channel.host
    socket.setNoDelay(true)
    channelConnected = false
    socket.on socketConnector.connectEvent, ->
      channelConnected = true
      channelReadyCallback(channel)

    socket.on 'readable', =>
      try
        data = socket.read()
        reader.addData(data) if data?
      catch error
        @logger.error "Failed to read data from backend socket. Error:", error
        channel.onDisconnect()

    socket.on 'error', (error) =>
      @logger.error "Socket error:", error
      unless channelConnected
        setTimeout @start, 0

    socket.on 'close', (had_error) =>
      channel.onDisconnect 'Backend socket closed'
      @logger.info "Socket closed."

  createSocketConnector: (channel) =>
    if channel.group is "ClusterManager"
      connect: @clusterClient.connect,
      connectEvent: 'connect'
    else
      connect: net.connect,
      connectEvent: 'connect'

  start: (callback) =>
      socket = net.connect @gatewayEndpoint
      socket.on 'connect', =>
        @logger.info "Connected to gateway service at:", @gatewayEndpoint
        socket.destroy()
        callback(null)
      socket.on 'error', (err) =>
        @logger.info 'Failed to connect to gateway service. Retrying in 2 seconds', err
        setTimeout(
          () => @start(callback),
          2000)



module.exports = (app, httpServer, callback) ->
  relay = new Relay(app)
  relay.initializeSocketIO(httpServer)
  relay.start(callback)
  return relay


