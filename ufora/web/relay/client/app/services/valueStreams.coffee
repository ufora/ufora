angular.module('pyfora')
  .factory 'valueStreams', ['ValueStream', (ValueStream) ->
    {
      empty: () -> new ValueStream()
      init: (arr) -> new ValueStream(arr)
    }
  ]


