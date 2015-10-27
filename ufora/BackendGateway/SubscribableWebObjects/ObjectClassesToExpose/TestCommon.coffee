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

doNothing = ()->
    return
errfun = (done) -> (value) -> done(Error(JSON.stringify(value)))
assertValueNull = (done) -> (value) ->
    if value?
        done(Error("Expected #{JSON.stringify(value)} to be null"))
    else
        done()

ensureCoresBooted = (webObjects, targetCount, continuation) ->
    desire = [[['ec2', 'c1.xlarge', 8], targetCount / 8]]
    finished = ()->
        toCall = continuation
        continuation = null
        if toCall?
            toCall()

    cores = new (webObjects[0].Cores)({})
    cores.setHardwareDesire desire,
        onSuccess: doNothing
        onFailure: ->
            console.error "failed to desire cores"
    cores.subscribe_numCpusActive
        onSuccess: (count) ->
            if count == targetCount
                finished()
        onChanged: (count) ->
            if count == targetCount
                finished()

expectResultImmediately = (targetValue, done) ->
    onSuccess: (value) ->
        if not value?
            if not targetValue?
                done()
            else
                done(Error("Expected #{JSON.stringify(targetValue)} but got #{JSON.stringify(value)}"))
        else
            value.should.equal(targetValue)
            done()
    onFailure: (value) ->
        done(Error("Expected #{JSON.stringify(targetValue)} but got #{JSON.stringify(value)}"))

expectAnyResultImmediately = (done) ->
    onSuccess: (value) ->
        done()
    onFailure: (value) ->
        done(Error("Expected null but got #{JSON.stringify(value)}"))

expectAnyError = (done) ->
    onSuccess: (value) ->
        done(Error("Expected an error, got #{JSON.stringify(value)}"))
    onFailure: (value) ->
        done()

expectSuccess = (done) ->
    onSuccess: (value) -> done()
    onFailure: (value) -> done(Error("Expected success, got #{JSON.stringify(value)}"))

module.exports = 
    doNothing: doNothing
    errfun:errfun
    assertValueNull: assertValueNull
    ensureCoresBooted: ensureCoresBooted
    expectResultImmediately: expectResultImmediately
    expectAnyResultImmediately: expectAnyResultImmediately
    expectAnyError: expectAnyError
    expectSuccess: expectSuccess


