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

fs = require 'fs'
version_line = fs.readFileSync('../../../packages/python/pyfora/_version.py',
                               'utf8'
                              ).trim().split('\n').pop()
console.info('Read version:', version_line)
version = version_line.match(/__version__ = \'(\S+)\'/)[1]

console.info("server.coffee starting. Version:", version)


config = require('./server/arguments')(version)
console.info("server.coffee parsed arguments")

logger = require './server/logging'
logger.info "relay logging initialized"
config.logger = logger

process.on 'uncaughtException', (err) ->
    logger.error "server.coffee caught root exception: %j", err
    for line in err.stack.split('\n')
        logger.error line


express = require 'express'
app = express()

app.set 'view engine', 'pug'
app.set 'views', __dirname + '/client'

app.use '/js', express.static('public/js')

app.get '/', (req, res) ->
    res.render 'index', {version: version}

httpServer = require('http').createServer(app)
relay = require('./server/relay') config, httpServer, () ->
    logger.info("relay app initialization callback fired")

    httpServer.listen config.port
    logger.info "HTTP listening on", config.port

