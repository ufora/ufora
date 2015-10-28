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

logger.info "server.coffee configured for:", process.env.NODE_ENV

logger.initialize 'debug'
logger.info "relay logging initialized"

process.stdout.write("server.coffee initialized logging\n")

app.set 'logger', logger

httpPort = app.get 'port'

logger.info("relay app initialization starting")

httpServer = require('http').createServer(app)
relay = require('./server/relay') app, httpServer, () ->
    logger.info("relay app initialization callback fired")

    httpServer.listen httpPort
    logger.info "HTTP listening on", httpPort

app.set 'relay', relay

