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
path = require 'path'
temp = require 'temp'
uuid = require 'node-uuid'
fs = require 'fs'
s3 = require '../aws/localS3'

uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/

newLocalS3= ->
    s3Path = temp.mkdirSync 'fakeS3_'
    new s3.LocalS3 s3Path

describe 'LocalS3', ->
    localS3 = newLocalS3()
    it 'should instantiate successully', ->
        localS3.should.not.be.null

    describe "#listUploads", ->
        it 'should initially return no uploads', (done) ->
            verifyNoPendingUploads localS3, done
        it 'should return in-progress uploads', (done) ->
            filePath = path.join(localS3.inProgressUploadsPath, 'id::key')
            partsFilePath = filePath + '.parts'
            fs.writeFileSync filePath, 'File data'
            fs.writeFileSync partsFilePath, new Date().toJSON()
            localS3.listUploads (err, uploads) ->
                should.not.exist err
                uploads.length.should.equal 1
                uploads[0].key.should.equal 'key'
                uploads[0].uploadId.should.equal 'id'
                done()

    describe "#abortUpload", ->
        it 'should remove in-progress uploads', (done) ->
            localS3.listUploads (err, uploads) ->
                uploads.length.should.equal 1
                localS3.abortUpload uploads[0], (err) ->
                    should.not.exist err
                    verifyNoPendingUploads localS3, done

    describe "#beginMultiPartUpload", ->
        anUpload = null
        it 'should return a valid upload object', (done) ->
            beginNewUpload localS3, (upload) ->
                anUpload = upload
                upload.should.have.property 'key'
                upload.key.should.equal 'key'

                upload.should.have.property 'uploadId'
                upload.uploadId.should.match uuidRegex

                upload.should.have.property 'initiated'
                Date.parse(upload.initiated).should.be.ok
                done()
        it 'should be possible to view the resulting upload using #listUploads', (done) ->
            should.exist anUpload
            localS3.listUploads (err, uploads) ->
                should.not.exist err
                uploads.length.should.equal 1
                uploads[0].should.deep.equal anUpload
                done()
        it 'should be possible to abort the new upload', (done) ->
            should.exist anUpload
            localS3.abortUpload anUpload, (err) ->
                should.not.exist err
                verifyNoPendingUploads localS3, done

    describe "#uploadPart", ->
        anUpload = null
        testData = 'Test data 0\n'
        firstPart = null
        it 'should be possible to upload a part to a new upload', (done) ->
            beginNewUpload localS3, (upload) ->
                anUpload = upload
                localS3.uploadPart upload, testData, (err, part) ->
                    should.not.exist err
                    part.should.be.ok
                    part.should.have.property 'partNumber'
                    part.partNumber.should.equal 0
                    part.should.have.property 'size'
                    part.size.should.equal testData.length
                    part.should.have.property 'etag'
                    part.etag.should.match uuidRegex
                    firstPart = part

                    verifyUploadFileContent localS3, upload, testData

                    partsFilePath = localS3.makeUploadPartsFilePath upload
                    lines = fs.readFileSync(partsFilePath, 'utf8').split('\n')
                    parts = (localS3.parsePart(line) for line, ix in lines when ix > 0 and line.length > 0)
                    parts.length.should.equal 1
                    parts[0].partNumber.should.equal part.partNumber
                    parts[0].size.should.equal part.size
                    parts[0].etag.should.equal part.etag
                    done()
        it 'should be possible to see the uploaded part in #listParts', (done) ->
            anUpload.should.not.be.null
            firstPart.should.not.be.null
            localS3.listParts anUpload, (err, parts) ->
                should.not.exist err
                parts.should.be.ok
                parts.length.should.equal 1
                parts[0].should.deep.equal firstPart
                done()
        it 'should be possible to upload more parts', (done) ->
            anUpload.should.not.be.null
            uploadTestParts localS3, anUpload, (err) ->
                should.not.exist err
                verifyUploadFileContent localS3, anUpload, testDataContent
                done()
        it 'should be possible to see all parts in #listParts', (done) ->
            anUpload.should.not.be.null
            localS3.listParts anUpload, (err, parts) ->
                should.not.exist err
                parts.should.be.ok
                parts.length.should.equal 4
                parts.every (part) -> part.size.should.equal testData.length
                done()
        it 'should be possible to finish the upload', (done) ->
            anUpload.should.not.be.null
            localS3.finishMultiPartUpload anUpload, (err) ->
                should.not.exist err
                fs.existsSync(localS3.makeUploadPath anUpload).should.be.false
                verifyKeyFileContent localS3, anUpload, testDataContent
                done()
        it 'should not be possible to abort a finished upload', (done) ->
            anUpload.should.not.be.null
            localS3.abortUpload anUpload, (err) ->
                err.message.should.equal 'NoSuchUpload'
                done()
        it 'should be possible to delete the new key', (done) ->
            anUpload.should.not.be.null
            localS3.deleteKeys [anUpload.key], (err) ->
                should.not.exist err
                fs.existsSync(localS3.makeKeyPath(anUpload.key)).should.be.false
                done()

    describe '#deleteKeys', ->
        it 'should be able to delete multiple keys', (done) ->
            uploadSeveralKeys localS3, (err) ->
                should.not.exist err
                fs.existsSync(localS3.makeKeyPath("key_#{i}")).should.be.true for i in [0...4]
                localS3.deleteKeys ("key_#{i}" for i in [0...4]), (err) ->
                    should.not.exist err
                    fs.existsSync(localS3.makeKeyPath("key_#{i}")).should.be.false for i in [0...4]
                    done()

    verifyNoPendingUploads = (localS3, callback) ->
        localS3.listUploads (err, uploads) ->
            should.not.exist err
            uploads.length.should.equal 0
            callback()

    beginNewUpload = (localS3, callback) ->
        localS3.beginMultiPartUpload 'key', (err, upload) ->
            should.not.exist err
            should.exist upload
            callback upload

    uploadTestParts = (localS3, upload, callback) ->
        async.forEachSeries [1...4],
            (index, callback) ->
                localS3.uploadPart upload, "Test data #{index}\n", (err, part) ->
                    return callback(err) if err?
                    callback()
            , callback

    testDataContent = ("Test data #{index}\n" for index in [0...4]).join('')

    verifyUploadFileContent = (localS3, upload, expectedContent) ->
        uploadPath = localS3.makeUploadPath upload
        verifyFileContent uploadPath, expectedContent

    verifyKeyFileContent = (localS3, upload, expectedContent) ->
        keyPath = localS3.makeKeyPath upload.key
        verifyFileContent keyPath, expectedContent

    verifyFileContent = (filePath, expectedContent) ->
        fs.existsSync(filePath).should.be.true
        fs.readFileSync(filePath, 'utf8').should.equal expectedContent

    uploadSeveralKeys = (localS3, callback) ->
        async.forEachSeries [0...4],
            (index, cb) ->
                localS3.beginMultiPartUpload "key_#{index}", (err, upload) ->
                    return cb(err) if err?
                    uploadTestParts localS3, upload, (err) ->
                        return cb(err) if err?
                        localS3.finishMultiPartUpload upload, cb
            , callback



