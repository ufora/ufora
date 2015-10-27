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

crypto = require('crypto')
knox = require('knox')
Henry = require('henry')
logger = require('../logging')
xml2js = require('xml2js')
parser = new xml2js.Parser()

urlExpiration = 300
contentType = 'application/octet-stream'

uploadBucket = null
henry = null
knoxClient = null
clientCallbacks = []

getParsedResponse = (req, callback, onSend) ->
    req.on 'response', (res) ->
        body = ''
        res.setEncoding('utf-8')
        res.on 'data', (chunk) -> body += chunk
        res.on 'end', () ->
            parser.parseString body, (err, body) ->
                callback err, body, res

    if onSend? then onSend(req) else req.end()

getEnvironmentCredentials = (bucketName) ->
    credentials =
        bucket: bucketName

    key = process.env.AWS_ACCESS_KEY_ID
    if key? then credentials.key = key else return null

    secret = process.env.AWS_SECRET_ACCESS_KEY
    if secret? then credentials.secret = secret else return null

    return credentials

module.exports.connectToBucket = (bucketName) ->
    uploadBucket = bucketName
    
    credentials = getEnvironmentCredentials bucketName
    if credentials?
        knoxClient = knox.createClient(credentials)

getS3Client = (callback) ->
    return callback(null, knoxClient) if knoxClient?

    # get role-based S3 client
    if clientCallbacks.push(callback) is 1 and not henry?
        henry = new Henry()
        henry.refresh (err, credentials) ->
            if err?
                logger.error "Failed to retrieve credentials from metadata endpoint: #{err}"
                return callback(err)

            credentials.bucket = uploadBucket
            knoxClient = knox.createClient(credentials)
            logger.info "Created knox client with access key: #{credentials.key}"

            henry.add knoxClient, null, (err, credentials) ->
                if err?
                    logger.error("Failed to get AWS credentials: #{err}")
                else
                    logger.info "updated credentials", credentials.key

                while clientCallbacks.length > 0
                    cb = clientCallbacks.shift()
                    cb(err, knoxClient)
            henry.start()

module.exports.listParts = (upload, callback) ->
    requestUrl = "/#{encodeURI(upload.key)}?uploadId=#{encodeURIComponent(upload.uploadId)}"
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request('GET', requestUrl )
        getParsedResponse req, (err, body, res) ->
            if err?
                logger.error "AWS request to list upload parts for #{upload.key} returned " +
                    "invalid xml: #{err}"
                return callback err

            if res.statusCode == 200
                logger.info "AWS request to list upload parts for #{upload.key} succeeded."

                data = []
                if body.Part?
                    parts = if body.Part instanceof Array then body.Part else [body.Part]
                    for part in parts
                        data.push
                            partNumber: parseInt(part.PartNumber)
                            size: parseInt(part.Size)
                            etag: part.ETag

                return callback(null, data)

            logger.error "AWS request to list upload parts #{upload.key} failed: #{res.statusCode}, %j",
                body
            callback(res)

module.exports.listSlices = (prefix, callback) ->
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request('GET', "/?prefix=#{encodeURIComponent(prefix)}")
        getParsedResponse req, (err, body, res) ->
            if err?
                logger.error "AWS request to list keys with prefix '#{prefix}' " +
                    "returned invalid xml: #{err}"
                return callback(err)

            if res.statusCode == 200
                logger.info "AWS request to list keys with prefix '#{prefix}' succeeded."

                data = []
                if body.Contents?
                    for contents in body.Contents
                        data.push
                            key: contents.Key
                            size: parseInt(contents.Size)
                return callback(null, data)

            logger.error "AWS request to list keys with prefix '#{prefix}' " +
                "failed: #{res.statusCode}, %j", body
            callback(res)

module.exports.listUploads = (callback) ->
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request('GET', '/?uploads')

        getParsedResponse req, (err, body, res) ->
            if err?
                logger.error "AWS request to list uploads returned invalid xml: #{err}"
                return callback(err)

            if res.statusCode is 200
                logger.info "AWS request to list uploads succeeded. %s", JSON.stringify(body, null, 2)

                uploads = []
                if body.Upload?
                    uploads = if body.Upload instanceof Array then body.Upload else [body.Upload]
                return callback null, (convertUploadFromAwsResponse(upload) for upload in uploads)
            logger.error "AWS request to list uploads failed: #{res.statusCode}, %j", body
            callback(res)

convertUploadFromAwsResponse = (upload) ->
    result =
        initiated: new Date(upload.Initiated)
        key: upload.Key
        uploadId: upload.UploadId
    return result

module.exports.abortUpload = (upload, callback) ->
    getS3Client (err, client) ->
        return callack(err) if err?
        req = client.request(
            'DELETE',
            "/#{encodeURI(upload.key)}?uploadId=#{encodeURIComponent(upload.uploadId)}"
            )

        getParsedResponse req, (err, body, res) ->
            if err?
                logger.error "AWS request to abort upload of #{upload.key} returned invalid xml:#{err}"
                return callback(err)

            if res.statusCode == 204
                logger.info "AWS request to abort upload of #{upload.key} succeeded."
                return callback()
            logger.error "AWS request to abort upload of #{upload.key} failed: #{res.statusCode}, %j",
                res.headers
            callback(res)

module.exports.uploadPart = (upload, data, callback) ->
    lastPart = upload.parts.length
    nextPart = lastPart + 1
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request(
            'PUT',
            "/#{encodeURI(upload.key)}?" +
                "partNumber=#{nextPart}&" +
                "uploadId=#{encodeURIComponent(upload.uploadId)}",
            {'Content-Length': data.length}
        )

        getParsedResponse req,
            (err, body, res) ->
                if err?
                    logger.error(
                        "AWS request to upload part #{nextPart} for #{upload.key} "
                        "returned invalid xml: #{err}"
                        )
                    return callback(err)

                if res.statusCode == 200
                    logger.info(
                        "AWS request to upload part #{nextPart} for #{upload.key} succeeded.%j",
                        res.headers
                        )
                    return callback null,
                        partNumber: nextPart
                        size: data.length
                        etag: res.headers.etag
                logger.error(
                    "AWS request to upload part #{nextPart} for #{upload.key} failed: "
                        "#{res.statusCode}, %j",
                    body
                    )
                callback(res)
            ,
            (req) ->
                # Send the chunks
                req.write data

                # Finish the request
                req.end(null, 'binary')

module.exports.finishMultiPartUpload = (upload, callback) ->
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request(
            'POST',
            "/#{encodeURI(upload.key)}?uploadId=#{encodeURIComponent(upload.uploadId)}"
            )

        getParsedResponse req,
            (err, body, res) ->
                if err?
                    logger.error(
                        "AWS request to finish upload for #{upload.key} returned invalid xml: #{err}"
                        )
                    return callback(err)

                if res.statusCode == 200
                    logger.info("AWS request to finish upload for #{upload.key} succeeded. %j", body)
                    return callback() #We've uploaded this part to S3

                logger.error(
                    "AWS request to finish for #{upload.key} failed: #{res.statusCode}, %j", body
                    )
                callback(res)
            ,
            (req) ->
                req.write("<CompleteMultipartUpload>")
                for part in upload.parts
                    req.write("<Part>")
                    req.write("<PartNumber>#{part.partNumber}</PartNumber>")
                    req.write("<ETag>#{part.etag}</ETag>")
                    req.write("</Part>")
                req.write("</CompleteMultipartUpload>")
                req.end()

module.exports.beginMultiPartUpload = (key, callback) ->
    uri = "/upload/#{key}"
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request('POST', "/#{encodeURI(key)}?uploads")

        getParsedResponse req, (err, body, res) ->
            if err?
                logger.error(
                    "AWS request to begin multi-part upload for #{key} returned invalid xml: #{err}"
                    )
                return callback(err)

            if res.statusCode == 200
                logger.info("AWS request to begin multi-part upload for #{key} succeeded.")
                return callback null,
                    initiated: new Date(body.Initiated)
                    key: body.Key
                    uploadId: body.UploadId
            logger.error(
                "AWS request to begin multi-part upload for #{key} failed: #{res.statusCode}, %j",
                body
                )
            callback(res)

        logger.info("AWS request to begin multi-part upload for #{key} started.")

module.exports.deleteKeys = (keys, callback) ->
    getS3Client (err, client) ->
        return callback(err) if err?
        req = client.request('POST', '/?delete')

        getParsedResponse req,
            (err, body, res) ->
                if err?
                    logger.error "Failed to delete keys #{keys}. AWS returned invalid xml: #{err}"
                    return callback(err)

                if res.statusCode is 200
                    logger.info "Successfully deleted keys #{keys}"
                    return callback()

                logger.error "Failed to delete keys #{keys}: #{res.statusCode}, %j", body
                callback(res)
            ,
            (req) ->
                req.write "<Delete>"
                req.write "<Quiet>true</Quiet>"
                req.write "<Object><Key>#{key}</Key></Object>" for key in keys
                req.write "</Delete>"
                req.end()


