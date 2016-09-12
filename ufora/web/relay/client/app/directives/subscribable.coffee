angular.module('pyfora')
  .directive 'subscribable', (subscribableObjects) ->
    restrict: 'A'
    link: (scope, elem, attrs) ->
      definition = scope.$eval attrs['subscribable']
      subscribableObjects.then (swo) ->
        portals = swo.link(definition, scope)
        _.each portals, (portal, name) ->
          portalName = portal._defs.as || name
          if scope[portalName]
            throw "The scope already has the variable #{portalName}.
                   Choose some other name for subscribable binding"

          scope[portalName] = portal
          _.each portal._settables, (name) ->
            scope.$watch "#{portalName}.#{name}", (value) ->
              swo.set portal, name, value
        scope.$on '$destroy', () ->
          _.each portals, (portal, name) ->
            swo.unsubscribe portal
