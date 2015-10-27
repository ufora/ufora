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

# Routes related to user management.
# e.g. login, logout, signup, etc.
#

async = require 'async'
logger = null

module.exports = (app) ->
    logger = app.get 'logger'
    interfaceKey = app.get 'interfaceKey'

    login_get:  (req, res) ->
        args =
            title: 'Login'
            url: req.url
            errormsg: req.flash('error')
            interfaceKey: interfaceKey
            clusterType: app.get 'clustertype'
        res.render 'login', args

    logout_get: (req, res) ->
        req.logout()
        res.redirect('/')

    request_invitation_get: (req, res) ->
        args =
            title: 'Request Invitation'
            url: req.url
            first_name: ''
            last_name: ''
            email: ''
            email_code: ''
            clusterType: app.get 'clustertype'

        unless req.query.code?
            logger.info "Request invitation with no email code"
            return res.render 'request_invitation', args

        args.email_code = req.query.code

        logger.info "Request invitation with email code: #{req.query.code}"
        app.get('auth').candidateFromEmailCode req.query.code, (err, candidate) ->
            if candidate? and not err?
                args.first_name = candidate.first_name
                args.last_name = candidate.last_name
                args.email = candidate.email
            res.render 'request_invitation', args

    request_invitation_post: (req, res) ->
        unless req.body.first_name? and req.body.last_name? and req.body.email?
            logger.warn "Invitation request with missing fields: #{req.body}"
            return res.send 400, 'Missing required field(s)'

        logger.info "Invitation request: %j", req.body

        auth = app.get 'auth'
        async.series [
            (cb) -> auth.addInvitationRequest req.body, cb
            (cb) ->
                requester =
                    first_name: req.body.first_name
                    last_name: req.body.last_name
                    email: req.body.email
                app.get('email').sendInvitationRequestConfirmation requester, cb
            (cb) ->
                return cb(null) unless req.query.code?
                auth.deleteCandidateEmailCode req.query.code, (err) ->
                    logger.warn "Failed to delete candidate email code: #{req.query.code}.
                        Error: #{err}" if err?
                    cb(null) # continue anyway
            (cb) ->
                auth.deleteCandidate req.body.email, (err) ->
                    logger.warn "Failed to delete candidate #{req.body.email}.
                        Error: #{err}" if err?
                    cb(null) #continue anyway
            ],
            (err) ->
                if err?
                    return res.send(err.status, err.message) if err.status?
                    return res.send 500, "Internal server error"
                res.send 200

    signup_get: (req, res) ->
        args =
            title: "Sign up"
            url: req.url
            first_name: ''
            last_name: ''
            email: ''
            error: ''
            clusterType: app.get 'clustertype'

        unless req.query.invite?
            args.error = "no-invite-code"
            return res.render 'signup', args

        auth = app.get 'auth'
        auth.getInvitation req.query.invite, (err, invitation) ->
            if err? or not invitation?
                logger.warn "Couldn't find invitation code #{req.query.invite}. Error: #{err}"
                args.error = "invalid-invite-code"
                return res.render 'signup', args
            args.first_name = invitation.first_name
            args.last_name = invitation.last_name
            args.email = invitation.email
            res.render 'signup', args

    signup_post: (req, res, next) ->
        logger.info "signing up user: #{req.body?.first_name} #{req.body?.last_name} <#{req.body?.email}>"
        unless req.query.invite?
            return res.send 400, "Missing invitation code"

        try
            validateSignupData req.body
        catch err
            return res.send 400, err.message

        auth = app.get 'auth'
        auth.getInvitation req.query.invite, (err, invitation) ->
            if err? or not invitation?
                return res.send 400, "Invalid invitation code"
            auth.createAccount req.body, (err, account) ->
                if err?
                    logger.error "Failed to create account for <#{req.body.email}>. Error: #{err}"
                    return res.send(err.status, err.message) if err.status?
                    return res.send 500, "Failed to create account"
                auth.deleteInvitation invitation.invite_code, (err) ->
                    if err?
                        logger.error "Failed to delete invitation after creating account: <#{req.body.email}>. #{err}",
                            invitation
                    req.body.username = req.body.email
                    auth.authenticate_request req, res, next, (err, user, message) ->
                        return res.send 500, "Failed to log in" if err?
                        return res.send 500, message unless user?


passwordRegex = /(?:(?=.*[a-z])(?:(?=.*[A-Z])(?=.*[\d\W])|(?=.*\W)(?=.*\d))|(?=.*\W)(?=.*[A-Z])(?=.*\d)).{8,}/

validateSignupData = (signup_info) ->
    unless signup_info.first_name? and signup_info.last_name? and signup_info.email? and
            signup_info.password?
        throw Error("Missing required fields")

    unless signup_info.password.match passwordRegex
        throw Error("Password doesn't meet complexity requirements")

    signup_info[key] = val.trim() for key, val of signup_info
    signup_info.id = emailToUserId(signup_info.email)

emailToUserId = (email) ->
    id = email.replace(/\W/g, '')
    id.replace(/^\d+/, '')


