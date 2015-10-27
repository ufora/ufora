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

###
MessageReader is a utility class used to read messages from a buffer.

Messages consist of a 4-byte header containing the message length followed by the message body.
MessageReader is constructed with a callback that is fired every time a complete message has
been read.
Clients repeatedly call addData, passing in data buffers read from a socket (or other input).
###

logger = require('./logging')

totalReaderCount = 0

verboseLogging = false

class MessageReader
    lengthBuffer: null
    lengthBufferOffset: 0
    length: null
    messageBuffer: null
    bufferOffset: 0
    readerID: null

    constructor: (@callback) ->
        @readerID = totalReaderCount
        @lengthBuffer = new Buffer(4)
        
        totalReaderCount = totalReaderCount + 1

    addData: (data) ->
        if verboseLogging
            logger.debug "reader #{@readerID}: given buffer of length #{data.length}"

        readOffset = 0
        while readOffset < data.length
            if not @length?
                numberOfBytesToCopy = Math.min(data.length - readOffset, 4 - @lengthBufferOffset)

                data.copy(
                    @lengthBuffer,
                    @lengthBufferOffset,
                    readOffset,
                    readOffset + numberOfBytesToCopy
                    )

                readOffset += numberOfBytesToCopy
                @lengthBufferOffset += numberOfBytesToCopy

                if numberOfBytesToCopy != 4
                    if verboseLogging
                        logger.debug (
                            "reader #{@readerID}: read #{numberOfBytesToCopy} in prefix size" + 
                            " read with lbo of #{@lengthBufferOffset}. " + 
                            "#{@lengthBuffer.toString('hex', 0, @lengthBufferOffset)}"
                            )

                if @lengthBufferOffset is 4
                    @length = @lengthBuffer.readUInt32LE(0)
                    if verboseLogging
                        logger.debug (
                            "reader #{@readerID}: read #{@length} as msg " + 
                            "size with #{data.length - readOffset} remaining. " + 
                            "#{@lengthBuffer.toString('hex')}"
                            )

                    if @length > 120*1024
                        logger.warn (
                            "reader #{@readerID}: Message reader got unexpectedly" + 
                            " long message of #{@length.toString(16)} bytes"
                            )
                    @messageBuffer = new Buffer(@length)
            else
                numberOfBytesToCopy = Math.min(data.length - readOffset, @length - @bufferOffset)
                data.copy(
                    @messageBuffer,
                    @bufferOffset,
                    readOffset,
                    readOffset + numberOfBytesToCopy
                    )
                @bufferOffset += numberOfBytesToCopy
                readOffset += numberOfBytesToCopy
                if @bufferOffset is @length
                    @callback(@messageBuffer)
                    @length = null
                    @lengthBufferOffset = 0
                    @messageBuffer = null
                    @bufferOffset = 0


module.exports.create = (callback) ->
    new MessageReader(callback)

module.exports.sendData = (socket, data) ->
    try
        length = new Buffer(4)
        length.writeUInt32LE(data.length, 0)
        socket.write(length)
        socket.write(data)
    catch error
        unless socket.disconnected?
            logger.error "Failed to write data to backend socket: #{error}"

