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

baseUrl = (req) ->
    "#{req.protocol}://#{req.host}/"

tosArgs = (req) ->
    base_url = baseUrl(req)
    title: 'Terms of Service'
    baseUrl: base_url
    privacyPolicyUrl: base_url + "legal/privacy"
    thirdPartyUrl: base_url + "content/3rdparty.html"
    url: req.url
    user: req.user

module.exports =
    # Standalond Terms of Service page
    getTos: (req, res) ->
        res.render 'tos', tosArgs(req)

    # Privacy Policy page
    getPrivacyPolicy: (req, res) ->
        base_url = baseUrl(req)
        res.render 'privacy',
            title: 'Privacy Policy'
            baseUrl: base_url
            tosUrl: base_url + "legal/tos"

    # Page where users are prompted to accept the TOS
    getAcceptTos: (req, res) ->
        res.render 'acceptTos', tosArgs(req)

    # POST user's acceptance of TOS
    postAcceptTos: (req, res) ->
        unless req.user?
            redirectTo = req.query.redirect ? '/tos'
            res.redirect "/login?redirect=#{encodeURIComponent(redirectTo)}"
            return

        req.user.acceptedTos()
        redirectTo = req.query.redirect ? '/'
        res.redirect redirectTo

