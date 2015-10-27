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

module.exports = (app) ->
    logger = app.get 'logger'

    sts = require '../sts'

    app.get '/sts/jwt', sts.get

    # Cumulus Web Adapter
    #####################

    # Allow cross origin requests
    app.all /\/api[/]?.*/, (req, res, next) ->
        res.header "Access-Control-Allow-Origin", req.headers.origin
        res.header "Access-Control-Allow-Headers", "X-Requested-With"
        res.header "Access-Control-Allow-Credentials", "true"
        next();

    app.all /\/api/, (req, res) ->
        logger.info 'Evaluating...', req.params[0]
        app.get('relay').processCumulusWebRequest(req, res, req.params[0], req.headers.accept)


