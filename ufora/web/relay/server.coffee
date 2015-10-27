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

process.stdout.write("server.coffee starting\n")

express = require 'express'
logger = require './server/logging'
path = require 'path'

process.on 'uncaughtException', (err) ->
    logger.error "server.coffee caught root exception: %j", err
    for line in err.stack.split('\n')
        logger.error line

app = express()

process.stdout.write("server.coffee got express\n")

require('./server/arguments').parse(app)

process.stdout.write("server.coffee parsed arguments\n")

app.set 'loglevel', 'debug'

logger.info "server.coffee configured for:", process.env.NODE_ENV

if process.env.NODE_ENV is 'test'
    app.use express.errorHandler()
logger.initialize app.get('loglevel')
logger.info "relay logging initialized"

process.stdout.write("server.coffee initialized logging\n")


app.set 'logger', logger

app.set 'views', __dirname + '/server/views'
app.set 'view engine', 'jade'

app.use express.favicon(__dirname + '/public/images/favicon.ico')
app.use express.logger('dev')
app.use express.bodyParser()
app.use express.methodOverride()

app.use express.compress
    filter: (req, res) ->
        if /.*gz$/.test(req.url)
            return false
        return true

app.use express.static(path.join(__dirname, 'public'))
app.use require('connect-flash')()
app.use logger.requestLogger

app.use app.router
app.use logger.requestErrorLogger # this middleware must come after app.router

require('./server/routes') app

httpPort = app.get 'port'

logger.info("relay app initialization starting")

httpServer = require('http').createServer(app)
relay = require('./server/relay') app, httpServer, () ->
    logger.info("relay app initialization callback fired")

    httpServer.listen httpPort
    logger.info "HTTP listening on", httpPort

app.set 'relay', relay

