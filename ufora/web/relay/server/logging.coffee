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

util = require('util')

log_levels =
    debug: 1
    info: 2
    warn: 3
    error: 4

logLevel = log_levels.info

getUserLogFile = (username)->
    if not logFile?
        return null
    extension = logFile.lastIndexOf('.')
    return "#{logFile.substring(0, extension)}.#{username}##{logFile.substr(extension)}"

log = (level, format, args...)->
    if log_levels[level] >= logLevel
        now = new Date()
        console[level]("#{now.toJSON()} - #{level}: #{format}", args...)

module.exports.initialize = (level) ->
    throw Error("Invalid log level '#{level}'") unless level of log_levels
    logLevel = log_levels[level]

module.exports.debug = debug = (format, args...) ->
    log('log', format, args...)

module.exports.info = info = (format, args...) ->
    log('info', format, args...)

module.exports.warn = warn = (format, args...) ->
    log('warn', format, args...)

module.exports.error = error = (format, args...) ->
    log('error', format, args...)

module.exports.attach = (socket) ->
    socket.debug = (format, args...) ->
        debug "<#{socket.user}> #{format}", args...
    socket.info = (format, args...) ->
        info "<#{socket.user}> #{format}", args...
    socket.warn = (format, args...) ->
        warn "<#{socket.user}> #{format}", args...
    socket.error = (format, args...) ->
        error "<#{socket.user}> #{format}", args...

requestPropertiesToLog = ['url', 'headers', 'method', 'httpVersion', 'originalUrl', 'query']

filterRequest = (originalReq) ->
    req = {}
    for propertyName in requestPropertiesToLog
        req[propertyName] = originalReq[propertyName] if propertyName of originalReq
    req.user = originalReq.user.id if originalReq.user?
    return req

module.exports.requestErrorLogger = (err, req, res, next) ->
    err.request = filterRequest(req)
    error("HTTP request error: #{err}\n#{err.stack}")
    next(err)

module.exports.requestLogger = (req, res, next) ->
    info("HTTP #{req.method} #{req.url}.\n#{JSON.stringify req, requestPropertiesToLog, 2}")
    next()

