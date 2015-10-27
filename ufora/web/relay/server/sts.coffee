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

# This module implements a Security Token Service that issues
# authorization tokens, which can be used to access backend
# resources such as SharedState, Cumulus, etc.

uuid = require('node-uuid')
jwt = require 'green-jwt'

signingKey = ''
module.exports.setSigningKey = (key) ->
    signingKey = key

module.exports.get = (req, res) ->
    unless req.user?
        res.writeHead 401, 'Unauthorized'
        res.end '<html><body><h1>Unauthorized</h1></body></html>'
        return

    token = issueToken
        prn: req.user.id
        aud: 'urn:ufora:services:sharedstate'
        ttl: 300
        is_admin: req.user.is_admin()
    res.end(token)

module.exports.issueToken = issueToken = ({prn, aud, ttl, is_admin}) ->
    nowInSeconds = Math.round(new Date().getTime()/1000)
    jwt_claim =
        iss: "ufora"
        exp: nowInSeconds + ttl
        iat: nowInSeconds
        aud: aud
        prn: prn
        jti: uuid.v4()
        authorizations: [
            {access: 'rw', prefix: (if is_admin then "" else "[[\"P\", \"users\"], [\"P\", \"#{prn}\"]"  )},
            {access: 'r', prefix: "[[\"P\", \"public\"]"},
            {access: 'rw', prefix: "[[\"P\", \"public\"], [\"P\", \"writeable\"],"},
            {access: 'rw', prefix: "[\"PersistentCacheIndex"},
            {access: 'r', prefix: '"__CLIENT_INFO_SPACE__"'}
            ]

    jwt.encode jwt_claim, signingKey

