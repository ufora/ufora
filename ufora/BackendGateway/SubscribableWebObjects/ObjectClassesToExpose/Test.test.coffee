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

testCommon = require './TestCommon'
chai = require '../../../web/relay/node_modules/chai'

should = chai.should()

expectResultImmediately = testCommon.expectResultImmediately
expectAnyResultImmediately = testCommon.expectAnyResultImmediately
expectAnyError = testCommon.expectAnyError
expectSuccess = testCommon.expectSuccess
errfun = testCommon.errfun

module.exports = (webObjects) ->
    testObject = null
    testCgLocationObject = null

    #initially, when we're setting the test up, 'webObjects' isn't populated
    Test = null
    TestCGLocation = null

    before ->
        Test = webObjects[0].Test
        TestCGLocation = webObjects[0].TestCGLocation
        testObject = new Test({})
        testCgLocationObject = new TestCGLocation({definition: 123})

    describe 'volumeTest', ->
        it 'should allow us to access many cg locations at once', (done)->
            @timeout 120000
            totalToTry = 15000
            totalReceived = 0
            totalSubmitted = 0
            maxToSubmitAtOnce = 100

            initialTimesFlushed = webObjects[0].incomingObjectCache.timesFlushed 

            checkIfDone = ()->
                if totalReceived == totalToTry
                    if webObjects[0].incomingObjectCache.timesFlushed == initialTimesFlushed
                        done(Error("The server never flushed the client object cache."))
                        return true
                    else
                        done()
                        return true
                else
                    return false

            submitOne = ->
                if totalSubmitted >= totalToTry
                    return

                location = new TestCGLocation({definition: totalSubmitted})
                location.get_testCgLocation 
                    onSuccess: (value)->
                        value.get_definition 
                            onSuccess: (defValue) ->
                                totalReceived += 1

                                if checkIfDone()
                                    return

                                if totalSubmitted - totalReceived < maxToSubmitAtOnce
                                    submitOne()

                            onFailure: errfun(done)
                    onFailure: errfun(done)

                totalSubmitted++

                if totalSubmitted - totalReceived < maxToSubmitAtOnce
                    submitOne()

            submitOne()

    describe 'testCgLocationObject', ->
        it 'should allow us to access definition', (done)->
            testCgLocationObject.get_definition expectResultImmediately(123, done)

        it 'should allow us to access aValue', (done)->
            testCgLocationObject.get_aValue expectAnyResultImmediately(done)

        it 'should allow us to access depth', (done)->
            testCgLocationObject.get_depth expectResultImmediately(0, done)

        it 'should allow us to call aFunction', (done)->
            testCgLocationObject.aFunction 123, expectResultImmediately(null, done)

        it 'should allow us to call aFunctionExpectingCallback', (done)->
            testCgLocationObject.aFunctionExpectingCallback 123, expectResultImmediately(123, done)

        it 'subsequent accesses of the same CG property should be identical', (done)->
            firstValue = null

            testCgLocationObject.get_testCgLocation 
                onSuccess: (value)->
                    if value instanceof TestCGLocation
                        firstValue = value
                        testCgLocationObject.get_testCgLocation 
                            onSuccess: (value)->
                                if value is firstValue
                                    done()
                                else
                                    done(Error("Objects #{JSON.stringify(value)} != #{JSON.stringify(firstValue)}"))
                            onFailure: testCommon.errfun(done)
                    else
                        done(Error("Expected a TestCGLocation object"))
                onFailure: testCommon.errfun(done)


        it 'should not allow us to call anUnexposedFunction', (done)->
            if testCgLocationObject.anUnexposedFunction?
                done(Eror("Expected it to be null but it wasnt"))
            else
                done()

        it 'should allow us to send messages that access aFunction', (done)->
            jsonInterface = webObjects[0].getJsonInterface()
            req = 
                objectDefinition: testCgLocationObject.toJSONWireFormat()
                messageType: 'Execute'
                args: {}
                field: 'aFunction'

            jsonInterface.request req, (response) ->
                if response.responseType != 'ExecutionResult'
                    done(Error("Expected exception. got #{JSON.stringify(response)}"))
                else
                    done()

        it 'should not allow us to send messages that access anUnexposedFunction', (done)->
            jsonInterface = webObjects[0].getJsonInterface()
            req = 
                objectDefinition: testCgLocationObject.toJSONWireFormat()
                messageType: 'Execute'
                args: {}
                field: 'anUnexposedFunction'

            jsonInterface.request req, (response) ->
                if response.responseType != 'Exception'
                    done(Error("Expected exception. got #{JSON.stringify(response)}"))
                else
                    done()




    describe 'testObject', ->
        it 'should not be null', ->
            testObject.should.not.be.null

        describe 'methods exposed', ->
            it 'should expose get_aFloat', ->
                testObject.get_aFloat.should.not.be.null

            it 'should expose get_mutableValue', ->
                testObject.get_mutableValue.should.not.be.null

            it 'should expose set_mutableValue', ->
                testObject.set_mutableValue.should.not.be.null

            it 'should expose subscribe_mutableValue', ->
                testObject.subscribe_mutableValue.should.not.be.null

            it 'should expose aFunction', ->
                testObject.aFunction.should.not.be.null

        it 'should be able to subscribe before reading', (done)->
            testObject.subscribe_aFloat.should.not.be.null
            testObject.subscribe_aFloat
                onSuccess: (value) ->
                    value.should.equal .5
                    done()
                onChanged: (value) ->
                    value.should.equal 'changed value'
                    done()
                onFailure: (msg) ->
                    done(Error("Failed: #{JSON.stringify(msg)}"))

        it 'should expose aFloat as a readable property', (done)->
            testObject.get_aFloat.should.not.be.null
            testObject.get_aFloat 
                onSuccess: (value) ->
                    value.should.equal .5
                    done()
                onFailure: (msg) ->
                    done(Error("Failed: #{JSON.stringify(msg)}"))

        it 'should support mutableValue as a writeable property', (done)->
            testObject.set_mutableValue 'a value', expectSuccess(done)

        it 'should support mutableValue as a readable property', (done)->
            testObject.get_mutableValue 
                onSuccess: (value) ->
                    value.should.not.be.null
                    value.should.equal 'a value'
                    done()

        it 'should let us call aFunction', (done) ->
            testObject.aFunction {x:1, y:2, z:3},
                onSuccess: () ->
                    done()
                onFailure: (msg) ->
                    done(Error(JSON.stringify(msg)))

        it 'should now have the value "3" in mutableValue', (done) ->
            testObject.get_mutableValue
                onSuccess: (value) ->
                    value.should.not.be.null
                    value.should.equal 3
                    done()

        it 'should let us subscribe to the mutableValue', (done) ->
            testObject.subscribe_mutableValue
                onSuccess: (value) ->
                    value.should.equal 3
                onChanged: (value) ->
                    value.should.equal 'changed value'
                    done()

            testObject.set_mutableValue 'changed value',
                onSuccess: ->


        it ('should give us an error when we access a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.get_aValueThrowingAnArbitraryException
                onSuccess: (value) ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'Guid'
                    done()

        it ('should give us an error when we write to a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.set_aValueThrowingAnArbitraryException 'something',
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'Guid'
                    done()

        it ('should give us an error when we subscribe to a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.subscribe_aValueThrowingAnArbitraryException
                onSuccess: () ->
                    done(Error("Returned success!"))
                onChanged: () ->
                    done(Error("Called changed!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'Guid'
                    done()

        it ('should give us an error when we call a function ' + 
                                'that throws an exception in python'), (done) ->
            testObject.aFunctionThrowingAnArbitraryException 'an argument',
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'Guid'
                    done()


        it ('should give us an error when we access a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.get_aValueThrowingASpecificException
                onSuccess: (value) ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.equal 'swo exception: getter'
                    done()

        it ('should give us an error when we write to a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.set_aValueThrowingASpecificException 'something',
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.equal 'swo exception: setter'
                    done()

        it ('should give us an error when we subscribe to a property ' + 
                                'that throws an exception in python'), (done) ->
            testObject.subscribe_aValueThrowingASpecificException
                onSuccess: () ->
                    done(Error("Returned success!"))
                onChanged: () ->
                    done(Error("Called changed!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.equal 'swo exception: getter'
                    done()

        it ('should give us an error when we call a function ' + 
                                'that throws an exception in python'), (done) ->
            testObject.aFunctionThrowingASpecificException 'an argument',
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.equal 'swo exception: function call'
                    done()

        it ('should give us an error when we call a function ' + 
                                'that doesnt accept arguments'), (done) ->
            testObject.aFunctionNotAcceptingAnyArguments null,
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'Guid'
                    done()

        it ('should give us an error when we call a function ' + 
                                'that doesnt return valid json'), (done) ->
            testObject.aFunctionNotReturningJson 'an argument',
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'result was not valid json'
                    value.message.should.contain 'Guid'
                    done()

        it ('should give us an error when we access a field ' + 
                                'that doesnt return valid json'), (done) ->
            testObject.get_aFieldNotReturningJson
                onSuccess: () ->
                    done(Error("Returned success!"))
                onFailure: (value) ->
                    value.should.not.be.null
                    value.responseType.should.equal 'Exception'
                    value.message.should.contain 'result was not valid json'
                    value.message.should.contain 'Guid'
                    done()


        it 'should be recursively constructible', (done)->
            aTest = new Test(new Test(new Test(new Test({}))))

            aTest.get_depth
                onSuccess: (value) ->
                    value.should.equal 3
                    done()
                onFailure: (value) -> done(Error(JSON.stringify(value)))

        it 'should support linear serialization of exponentially pathed graphs', (done) ->
            t = new Test({})

            heights = for _ in [0..20]
                t2 = new Test([t,t])
                t = t2
                webObjects[0].flushObjectIds()
                stringified = JSON.stringify(t.toJSONWireFormat())
                stringified.length

            for t in [0..18]
                h1 = heights[t + 1] - heights[t + 0]
                h2 = heights[t + 2] - heights[t + 1]
                h1.should.be.within h2 - 30, h2 + 30

            done()
        


