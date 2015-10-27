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

async = require 'async'
fs = require 'fs'
path = require 'path'
S = require 'string'
temp = require 'temp'
uuid = require 'node-uuid'

class LocalS3
    constructor: (s3Path) ->
        @bucketPath = path.join s3Path, 'ufora.user.data'
        unless fs.existsSync s3Path
            fs.mkdirSync s3Path
        unless fs.existsSync @bucketPath
            fs.mkdirSync @bucketPath
        @inProgressUploadsPath = temp.mkdirSync 'uploads'

    listUploads: (callback) ->
        fs.readdir @inProgressUploadsPath, (err, files) =>
            return callback(err) if err?
            async.map (file for file in files when S(file).endsWith('.parts')),
                (file, callback) =>
                    fs.readFile @makeUploadPath(file), (err, data) =>
                        return callback(err) if err?
                        creationTime = S(data).lines()[0]
                        upload = @parseUploadFileName file[..(file.length-7)]
                        callback null,
                            initiated: new Date(creationTime)
                            key: upload.key
                            uploadId: upload.uploadId
                ,callback

    beginMultiPartUpload: (key, callback) ->
        upload =
            uploadId: uuid.v4()
            key: key
        fs.open @makeUploadPath(upload), 'w', (err, fd) =>
            return callback(err) if err?
            fs.close fd
            creationTime = new Date()
            upload.initiated = creationTime
            fs.writeFile @makeUploadPartsFilePath(upload), "#{creationTime.toJSON()}\n", (err) ->
                if err?
                    @abortUpload upload, ->
                    return callback(err)
                callback null, upload

    uploadPart: (upload, data, callback) ->
        @listParts upload, (err, parts) =>
            return callback(err) if err?
            fs.appendFile @makeUploadPath(upload), data, (err) =>
                return callback(err) if err?
                part =
                    partNumber: parts.length
                    size: data.length
                    etag: uuid.v4()
                fs.appendFile @makeUploadPartsFilePath(upload),
                    "#{part.partNumber},#{part.size},#{part.etag}\n", (err) =>
                        if err? then callback(err) else callback(null, part)

    finishMultiPartUpload: (upload, callback) ->
        fs.rename @makeUploadPath(upload), @makeKeyPath(upload.key), (err) =>
            return callback(err) if err?
            fs.unlink @makeUploadPartsFilePath(upload), callback

    abortUpload: (upload, callback) ->
        removeIfExists = (path, callback) ->
            fs.exists path, (exists) ->
                if exists then fs.unlink(path, callback) else callback()

        fs.exists @makeUploadPartsFilePath(upload), (exists) =>
            # we'll try to clean up everything but if the parts file doesn't exists we'll
            # return Error('NoSuchUpload')
            async.forEach [@makeUploadPath(upload), @makeUploadPartsFilePath(upload)],
                removeIfExists,
                (err) ->
                    return callback(err) if err?
                    callback(if exists then null else new Error('NoSuchUpload'))

    listParts: (upload, callback) ->
        fs.readFile @makeUploadPartsFilePath(upload), 'utf8', (err, data) =>
            return callback(err) if err?
            parts = (@parsePart(line) for line, index in data.split('\n') when index > 0 and line.length > 0)
            callback(null, parts)

    parsePart: (line) ->
        fields = line.split(',')
        {
            partNumber: parseInt fields[0]
            size: parseInt fields[1]
            etag: fields[2]
        }

    listSlices: (prefix, callback) ->
        fs.readdir @bucketPath, (err, files) =>
            return callback(err) if err?

            getStatsIfPrefixMatch = (file, callback) =>
                return callback(null, null) unless file.indexOf(prefix) is 0
                fs.stat path.join(@bucketPath, file), (err, stats) =>
                    return callback(err) if err?
                    callback null,
                        key: file
                        size: stats.size
            async.map files, getStatsIfPrefixMatch, (err, results) ->
                return callback(err) if err?
                callback null, results.filter((result) -> result?)

    deleteKeys: (keys, callback) ->
        async.forEachSeries keys,
            (key, cb) =>
                fs.unlink @makeKeyPath(key), cb
            , callback

    makeUploadPath: (input) ->
        return path.join(@inProgressUploadsPath, input) if typeof(input) is 'string'
        @makeUploadPath "#{input.uploadId}::#{input.key}"

    makeUploadPartsFilePath: (input) ->
        @makeUploadPath(input) + ".parts"

    makeKeyPath: (key) ->
        path.join @bucketPath, key

    parseUploadFileName: (path) ->
        parts = path.split '::'
        { key: parts[1], uploadId: parts[0]}

module.exports.LocalS3 = LocalS3
module.exports.initialize = (app) ->
    new LocalS3(app.get 'localS3Path')


