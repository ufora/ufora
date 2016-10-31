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

class Queue
    constructor: (@onItem, @maxLength) ->
        @isPaused = false
        @elements = []

    push: (element) ->
        @elements.push(element)
        if not @isPaused and @length() is 1
            process.nextTick @triggerCallback
        return @isAlmostFull()

    pop: ->
        @elements.shift()

    top: ->
        @elements[0]

    length: ->
        @elements.length

    isAlmostFull: ->
        @maxLength > 0 and @length() > @maxLength*0.75

    isFull: ->
        @maxLength > 0 and @length() >= @maxLength

    pause: ->
        @isPaused = true

    resume: ->
        @isPaused = false
        if @length isnt 0
            process.nextTick @triggerCallback

    triggerCallback: =>
        if @length() is 0
            return

        @onItem @top()
        @pop()
        @scheduleImmediately(@triggerCallback) if not @isPaused

    scheduleImmediately: (func) ->
        process.nextTick(func)



module.exports.create = (maxLength=-1, onItem) ->
    new Queue(onItem, maxLength)


