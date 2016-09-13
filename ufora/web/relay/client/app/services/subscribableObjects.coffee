class SocketIoJson
    constructor: (@socket) ->
        @messageId = 0
        @pending_callbacks = {}
        @on_unknown_message = ((msg)-> console.error("Unknown message: #{msg}"))

        @socket.on 'response', (data) =>
            message = JSON.parse(data)
            if not (message.messageId? and @pending_callbacks[message.messageId])
                @on_unknown_message(message)
                return

            callback = @pending_callbacks[message.messageId]
            if message.responseType != 'SubscribeResponse'
                delete @pending_callbacks[message.messageId]

            callback(message)


    request: (message, callback) =>
        messageId = @messageId
        @messageId += 1

        @pending_callbacks[messageId] = callback
        message.messageId = messageId

        @socket.emit 'message',
            body: JSON.stringify(message)


class SubscribablesService
    @mappings:
      cumulus: "ViewOfEntireCumulusSystem"

    constructor: (@subscribableWebObjects, @valueStreams) ->
        @cache = {}

    newInterface: (inter, args) ->
      self =
        _raw: new inter(args)
        _streams: {}
        set: (prop, value) ->
          self._raw["set_#{prop}"] value,
            onFailure: (msg) ->
              $log.error(msg)
            onSuccess: () ->
        subscribe: (prop, resubscribe) =>
          self._streams[prop] ||= @valueStreams.empty()
          self._raw["subscribe_#{prop}"]
            onFailure: (msg) ->
              $log.error(msg)
            onSuccess: (data) ->
              self._streams[prop].notify(data)
            onChanged: (data) ->
              self._streams[prop].notify(data)
              resubscribe()
          self._streams[prop]
        unsubscribe: (prop) ->
          console.trace("unsubscribing")
          self._raw["unsubscribe_#{prop}"]
            onFailure: (msg) ->
            onSuccess: () ->
      self

    getKey: (name, args) ->
      serializedArgs = _.chain(args)
        .keys()
        .inject(((memo, k) -> memo = memo.concat([k, args[k]])), [])
        .value()
        .join('-')
      "#{name}-#{serializedArgs}"

    getInterfaceInstance: (name, args) ->
      key = @getKey(name, args)
      name = SubscribablesService.mappings[name] or name
      @cache[key] ||= @newInterface(@subscribableWebObjects[name], args)

    subscribeProperty: (portal, propName) =>
      resubscribe = () => @subscribeProperty(portal, propName)
      portal._interface.subscribe(propName, resubscribe).each (value) ->
        portal[propName] = value
        portal._scope.$digest() if !portal._scope.$$phase
      portal[propName] = null

    unsubscribeProperty: (portal, propName) ->
      console.trace("unsubscribing #{propName}")
      portal._interface.unsubscribe(propName)

    set: (portal, propName, value) ->
      portal._interface.set(propName, value)

    subscribe: (portal) ->
      _.each portal._defs.properties, (propName) =>
        @subscribeProperty(portal, propName)

    unsubscribe: (portal) ->
      _.each portal._defs.properties, (propName) =>
        @unsubscribeProperty(portal, propName)

    getPortal: (name, defs, scope) ->
      interfaceInstance = @getInterfaceInstance(name, defs.args)
      settables = _.chain(interfaceInstance._raw)
        .keys()
        .filter((k) -> k.match(/\bset_/))
        .map((k) -> k.replace(/set_/, ''))
        .value()
      portal =
        _defs:  defs
        _name:  name
        _id:    _.uniqueId name
        _scope: scope
        _interface: interfaceInstance
        _settables: settables
      @subscribe portal
      portal

    link: (def, scope) ->
      _build = (memo, defs, name) =>
        memo[name] = @getPortal(name, defs, scope)
        memo
      _.inject def, _build, {}


angular.module('pyfora')
  .factory 'subscribableObjects', ($log, socketIo, valueStreams) ->
    new Promise (resolve, reject) ->
        socketIo.then (socket) ->
            socketIoJson = new SocketIoJson(socket)
            subscribables = SubscribableWebObjects(socketIoJson)
            resolve(new SubscribablesService(subscribables, valueStreams))
        .catch (err) ->
            reject(err)

