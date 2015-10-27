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

chai = require 'chai'
should = chai.should()

async = require 'async'

temp = require 'temp'
logger = require '../logging'
logger.initialize 'warn'
s3 = require '../aws/localS3'

fileUploader = require('../fileUploader')
    get: (id) ->
        return logger if id is 'logger'

newLocalS3= ->
    new s3.LocalS3(temp.mkdirSync 'fakeS3_')

newUploadManager = ->
    new fileUploader.UploadManager newLocalS3(), {}

deleteUploadedFile = (file) ->
    localS3 = newLocalS3()
    console.info "Bucket path: #{localS3.bucketPath}"
    localS3.listSlices "user_#{file.name}", (err, slices) ->
        return if err or slices.length is 0
        localS3.deleteKeys (slice.key for slice in slices), (err) ->
            console.error "Failed to delete file(s): #{err}"

describe 'UploadManager', ->
    testFileContent = ("test line #{i}" for i in [0...4]).join('\n')
    file =
        name: 'test.file'
        size: testFileContent.length
        mtime: Date()

    multiChunkFile =
        name: 'test.file'
        size: testFileContent.length * 10
        mtime: Date()

    verifyProgressEvent = (event, expectedBytes, fileToCheck) ->
        fileToCheck = file unless fileToCheck?
        should.exist event
        event.file.should.deep.equal fileToCheck
        event.bytesLoaded.should.equal expectedBytes

    it 'should instantiate successfully', ->
        newUploadManager().should.be.ok

    describe '#findUpload', ->
        manager = newUploadManager()
        it 'should return null for non-existent uploads', ->
            upload = manager.findUpload 'user',
                name: 'dummy.txt'
                size: 123
                mtime: new Date().toJSON()
            should.not.exist upload

    describe 'GC loop', ->
        manager = newUploadManager()
        it 'should start and stop successfully', ->
            manager.runGC()
            manager.stopGC()
        it 'should discard old uploads', (done) ->
            manager.gcFreq = 4
            manager.gcMaxAge = 2
            manager.uploadFile 'user', file, (progress) ->
                verifyProgressEvent progress, 0
                upload = manager.findUpload 'user', file
                should.exist upload
                manager.onGarbageCollection = (fileUpload) ->
                    if fileUpload.fileId is upload.fileId
                        manager.onGarbageCollection = (f) ->
                        manager.stopGC()
                        done()

                manager.runGC()

    describe '#uploadFile', ->
        manager = newUploadManager()
        it 'should succeed on first call', (done) ->
            manager.uploadFile 'user', file, (progress) ->
                verifyProgressEvent progress, 0
                done()
        it 'should succeed on subsequent call with the same file', (done) ->
            manager.uploadFile 'user', file, (progress) ->
                verifyProgressEvent progress, 0
                done()
        it 'should be returned from #findUpload', ->
            upload = manager.findUpload 'user', file
            should.exist upload
            upload.file.should.deep.equal file
        it 'should be possible to complete the upload in one chunk', (done) ->
            upload = manager.findUpload 'user', file
            upload.uploadChunk {data: new Buffer(testFileContent)}, (progress) ->
                verifyProgressEvent progress, file.size
                done()
        it 'should not be returned by #findUpload anymore', ->
            should.not.exist manager.findUpload('user', file)
        it 'should return the size of already uploaded files', (done) ->
            manager.uploadFile 'user', file, (progress) ->
                verifyProgressEvent progress, file.size
                should.not.exist manager.findUpload('user', file)
                done()

    describe '#uploadChunk', ->
        deleteUploadedFile(file)
        manager = newUploadManager()
        initiateUpload = (fileToUpload, bytesAlreadyUploaded, callback) ->
            manager.uploadFile 'user', fileToUpload, (progress) ->
                verifyProgressEvent progress, 0, multiChunkFile
                upload = manager.findUpload 'user', multiChunkFile
                should.exist upload

        uploadChunks = (upload, count, chunksAlreadyUploaded, callback) ->
            chunkCount = chunksAlreadyUploaded
            async.whilst(
                () ->
                    chunkCount < count
                (callback) ->
                    upload.uploadChunk {data: testFileContent}, (prog) ->
                        chunkCount++
                        verifyProgressEvent prog, testFileContent.length * chunkCount, multiChunkFile
                        callback(if prog.bytesLoaded is -1 then new Error("Failed to upload chunk #{chunkCount}") else null)
                (err) ->
                    callback(err)
            )

        it 'should be able to upload a couple of chunks', (done) ->
            manager.uploadFile 'user', multiChunkFile, (progress) ->
                verifyProgressEvent progress, 0, multiChunkFile
                upload = manager.findUpload 'user', multiChunkFile
                should.exist upload

                uploadChunks upload, 5, 0, (err) ->
                    should.not.exist err
                    done()

        it 'should show up in #findUpload', ->
            upload = manager.findUpload 'user', multiChunkFile
            should.exist upload
            upload.file.should.deep.equal multiChunkFile

        it 'should be possible to resume the upload', (done) ->
            manager.uploadFile 'user', multiChunkFile, (progress) ->
                verifyProgressEvent progress, 5 * testFileContent.length, multiChunkFile
                upload = manager.findUpload 'user', multiChunkFile
                should.exist upload

                uploadChunks upload, 10, 5, (err) ->
                    should.not.exist err
                    done()

        it 'should not be possible to retrieve finished uploads', (done) ->
            upload = manager.findUpload 'user', multiChunkFile
            should.not.exist upload
            done()

        it 'should not be possible to restart a finished upload', (done) ->
            manager.uploadFile 'user', multiChunkFile, (progress) ->
                verifyProgressEvent progress, 10 * testFileContent.length, multiChunkFile
                upload = manager.findUpload 'user', multiChunkFile
                should.not.exist upload
                done()


