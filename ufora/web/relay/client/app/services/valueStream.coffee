angular.module('pyfora')
  .factory 'ValueStream', ['$rootScope', ($rootScope) ->
    class ValueStream
      constructor: (values = []) ->
        @values = values
        @handlers = []
        @lastValue = undefined

      notify: (value) ->
        @appendValue(value)
        return

      each: (handler) ->
        @handlers.unshift handler
        return

      last: () -> return @lastValue || _.last(@values)

      appendValue: (value) ->
        @values.push value
        @runQueue()

      runQueue: () ->
        _run = () =>
          _.each @values, (value) =>
            _.each @handlers, (handler) =>
              handler(value)
            @lastValue = value
        if $rootScope.$$phase
          _run()
        else
          $rootScope.$apply _run 
        @values = []
  ]



