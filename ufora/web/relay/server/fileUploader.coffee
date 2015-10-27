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

logger = null

class UploadManager
    @sliceSize = 52428800
    @partSize = 5242880

    constructor: (@s3, {sliceSize, partSize, @gcFreq, @gcMaxAge})  ->
        UploadManager.sliceSize = sliceSize if sliceSize?
        UploadManager.partSize = partSize if partSize?

        @gcFreq ?= 3600000     # GC every hour
        @gcMaxAge ?= 86400000  # GC uploads older than 24 hours
        @uploadsInProgress = {}
        @gcTimer = null
        @onGarbageCollection = (fileUpload) ->

    newUploadFromAws: (s3Upload) ->
        [fileId, sliceNumber] = @fileIdAndSliceFromAwsUploadKey(s3Upload.key)
        new FileUpload @s3, @onUploadComplete, fileId, new SliceUpload(s3Upload, sliceNumber)

    newUploadFromFile: (fileId, file) ->
        upload = new FileUpload @s3, @onUploadComplete, fileId, null
        upload.file = file
        return upload

    onUploadComplete: (fileId, err) =>
        unless err?
            delete @uploadsInProgress[fileId]
            return
        @uploadsInProgress[fileId].abort =>
            delete @uploadsInProgress[fileId]

    fileIdAndSliceFromAwsUploadKey: (key) ->
        i = key.lastIndexOf("_")
        [key[...i], parseInt(key[i+1..])]

    makeFileIdentifier: (user, file) ->
        "#{user}_#{file.name}_#{file.size}_#{file.mtime}"

    findUpload: (user, file) ->
        fileId = @makeFileIdentifier(user, file)
        if fileId of @uploadsInProgress
            return @uploadsInProgress[fileId]
        return null

    isFileUploaded: (fileId, callback) ->
        @s3.listSlices fileId, (err, slices) =>
            return callback(err) if err
            size = 0;
            size += slice.size for slice in slices
            callback(null, size)

    uploadFile: (user, file, onProgress) ->
        fileId = @makeFileIdentifier(user, file)
        @isFileUploaded fileId, (err, bytesUploaded) =>
            if not err and bytesUploaded is 0
                upload = @findUpload user, file
                if upload?
                    upload.file = file
                    return upload.resume onProgress
                upload = @newUploadFromFile fileId, file
                @uploadsInProgress[upload.fileId] = upload
                return upload.nextSlice onProgress

            if err
                bytesUploaded = -1
            onProgress
                file: file
                fileId: fileId
                bytesLoaded: bytesUploaded

    runGC: =>
        watermark = new Date()
        watermark.setTime(watermark.getTime() - @gcMaxAge)
        @s3.listUploads (err, uploads) =>
            return logger.error("Failed to list old uploads.") if err?
            for s3Upload in uploads
                logger.info "Found in-progress upload to #{s3Upload.key}"
                fileUpload = @newUploadFromAws(s3Upload)
                if fileUpload.fileId not of @uploadsInProgress
                    @uploadsInProgress[fileUpload.fileId] = fileUpload
                if s3Upload.initiated < watermark
                    @onGarbageCollection(fileUpload)
                    fileUpload.abort ->
            @gcTimer = setTimeout(@runGC, @gcFreq)

    stopGC: ->
        clearTimeout(@gcTimer) if @gcTimer?
        @gcTimer = null

class FileUpload
    constructor: (@s3, @onCompleted, @fileId, @currentSlice) ->
        @bytesUploaded = 0
        @onProgress = null

    nextSlice: (onProgress) ->
        @onProgress = onProgress if onProgress?
        sliceIndex = 0
        if @currentSlice?
            sliceIndex = @currentSlice.index + 1
            @bytesUploaded += @currentSlice.bytesUploaded

        @s3.beginMultiPartUpload "#{@fileId}_#{sliceIndex}", (err, s3Upload) =>
            if err?
                logger.error("Failed to initiate multipart upload to #{fileId}. Error: #{err}")
                return @onCompleted(@fileId, err)
            @currentSlice = new SliceUpload(s3Upload, sliceIndex)
            @currentSlice.setParts()
            @resume()

    abort: (callback) ->
        cleanup = =>
            @deleteAllSlices ->
            @onCompleted(@fileId)
        return cleanup() unless @currentSlice?
        @s3.abortUpload @currentSlice.s3Upload, (err) =>
            if err?
                logger.error "Failed to abort upload. Error: #{err}"
            else
                logger.info "Aborted upload: %j", @currentSlice.s3Upload
            cleanup()
            callback(err)

    resume: (onProgress) ->
        @onProgress = onProgress if onProgress?
        return @reportSuccess() if @currentSlice.s3Upload.parts?
        @s3.listParts @currentSlice.s3Upload, (err, parts) =>
            if err?
                logger.error "Failed to list parts for upload #{@fileId}. Error: #{err}"
                return @reportFailure(err)

            reducer = (prev, curr) -> prev + curr.size
            bytesUploaded = parts.reduce reducer, 0
            @currentSlice.setParts parts
            @currentSlice.bytesUploaded = bytesUploaded

            @computeUploadedBytesInAllSlices (err, bytesUploaded) =>
                if err?
                    logger.error "Failed to compute uploaded bytes of in-progress upload " +
                        "#{@fileId}"
                    return @reportFailure(err)
                @bytesUploaded = bytesUploaded
                @resume()

    reportProgress: (bytesLoaded) ->
        @onProgress
            file: @file
            fileId: @fileId
            bytesLoaded: bytesLoaded

    reportFailure: (err) ->
        @onCompleted @fileId, err
        @reportProgress -1

    reportSuccess: ->
        @reportProgress @totalBytesUploaded()

    computeUploadedBytesInAllSlices: (callback) ->
        @s3.listSlices @fileId, (err, slices) =>
            return callback(err) if err?
            sumSizes = (prev, curr) =>
                if curr.key is @currentSlice.s3Upload.key then prev else prev + curr.size
            bytesUploaded = slices.reduce sumSizes, 0
            callback null, bytesUploaded

    uploadChunk: (data, onProgress) ->
        @onProgress = onProgress if onProgress?
        try
            @currentSlice.addChunk(new Buffer(data.data, 'binary'))
            if @shouldUploadPart()
                @uploadPart()
            else
                @reportSuccess()
        catch error
            logger.error "Unexpected exception uploading data chunk:", error
            @reportFailure error

    shouldUploadPart: ->
        @currentSlice.currentPart.size >= UploadManager.partSize or @isEndOfFile()

    uploadPart: ->
        logger.info "Uploading file part with #{@currentSlice.currentPart.chunks.length} chunks.
            Size = #{@currentSlice.currentPart.size}."
        @s3.uploadPart @currentSlice.s3Upload, Buffer.concat(@currentSlice.currentPart.chunks),
            (err, part) =>
                if err?
                    logger.error "Failed to upload part for #{@currentSlice.s3Upload.key}"
                    return @reportFailure(err)

                @currentSlice.addPart part
                if @isEndOfSlice()
                    logger.info "Finishing multi-part upload for slice #{@currentSlice}
                        Total size so far: #{@totalBytesUploaded()}"
                    @s3.finishMultiPartUpload @currentSlice.s3Upload, (err) =>
                        if err?
                            logger.error "Failed to complete upload for " +
                                "#{@currentSlice.s3Upload.key}"
                            return @reportFailure(err)

                        if @totalBytesUploaded() < @file.size
                            @nextSlice null, (err)->
                        else
                            @onCompleted @fileId
                            @reportSuccess()
                else
                    @reportSuccess()

    totalBytesUploaded: ->
        @bytesUploaded + @currentSlice.bytesUploaded + @currentSlice.currentPart.size

    isEndOfSlice: ->
        return @isEndOfFile() or @currentSlice.bytesUploaded >= UploadManager.sliceSize

    isEndOfFile: ->
        return @totalBytesUploaded() is @file.size

    deleteAllSlices: (callback) ->
        @s3.deleteKeys ("#{@fileId}_#{i}" for i in [0..@currentSlice.index]), callback

class SliceUpload
    constructor: (@s3Upload, @index) ->
        @bytesUploaded = 0
        @resetCurrentPart()

    addPart: (part) ->
        @s3Upload.parts.push part
        @bytesUploaded += part.size
        @resetCurrentPart()

    addChunk: (chunk) ->
        @currentPart.chunks.push chunk
        @currentPart.size += chunk.length

    setParts: (parts) ->
        @s3Upload.parts = if parts? then parts else []

    resetCurrentPart: ->
        @currentPart =
            chunks: []
            size: 0

module.exports = (app) ->
    logger = app.get 'logger'

    UploadManager: UploadManager
    FileUpload: FileUpload


