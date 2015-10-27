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

queue = require('./queue')

exports.testCreate = (test) ->
    q = queue.create 3, (item) ->
        test.ok true, "callback fired"

    test.expect 4
    test.equal q.maxLength, 3
    test.equal q.length(), 0
    test.ok(not q.isFull())
    q.onItem null, null

    test.done()

exports.testPush = (test) ->
    maxLength = 3
    itemCount = 2
    callbackCount = 0
    q = queue.create maxLength, (item) ->
        test.equal item, callbackCount
        if ++callbackCount is itemCount
            test.ok true, 'all items received'
            test.done()

    test.expect itemCount*2 + 1
    for i in [0...itemCount]
        test.ok(not q.push(i))


exports.testOverflow = (test) ->
    maxLength = 4
    itemCount = 5
    q = queue.create maxLength, (item) ->
        #test.ok false, "Callback fired on paused queue"
    q.pause()

    test.expect itemCount
    for i in [1..itemCount-2]
        test.ok(not q.push(i))
    test.ok(q.push(itemCount - 1))
    test.ok(q.push(itemCount))

    test.done()

exports.testPop = (test) ->
    q = queue.create(3, (item)->
        )

    test.expect 4
    q.pause()
    test.ok(q.isPaused)
    for i in [0...3]
        q.push(i)
        test.equal(q.pop(), i)
    test.done()






