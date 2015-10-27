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

async = require 'async'
fs = require 'fs'
carrier = require 'carrier'
url = require 'url'
email = require '../email'

app = null
logger = null

module.exports =  (express_app) ->
    app = express_app
    logger = app.get 'logger'

    result = (req, res) ->
        res.render 'admin',
            title: 'UFORA Administration'

    result.get_accounts = (req, res) ->
        app.get('auth').listUsers null, null, (err, users) ->
            res.render 'accounts',
                users: users

    result.get_invitation_requests = (req, res) ->
        app.get('auth').listInvitationRequests null, null, (err, requests) ->
            res.render 'invitation_requests',
                requests: requests

    result.get_pending_invitations= (req, res) ->
        app.get('auth').listPendingInvitations null, null, (err, invitations) ->
            res.render 'pending_invitations',
                invitations: invitations

    result.get_candidates = (req, res) ->
        app.get('auth').listCandidates null, null, (err, candidates) ->
            res.render 'candidates',
                candidates: candidates

    result.uploadCandidates = (req, res) ->
        res.send 400 unless req.files.candidates? and req.files.candidates.length > 0
        processCandidateFile req.files.candidates[0],
            (err, results) ->
                if err?
                    return res.send 400, err

                logger.info "finished process files err: #{err}, results: %j", results
                res.send 200, "Thanks!"

    result.newCandidate = (req, res) ->
        try
            validateNameAndEmail req.body
        catch err
            logger.warn "Invalid new candidate request. Error: #{err}"
            return res.send 400, err.message
        app.get('auth').addCandidate req.body, (err) ->
            if err?
                logger.error "Failed to add candidate: #{err}"
                return res.send(err.status, err.message) if err.status?
                return res.send 500, "Failed to add candidate"
            res.send 200

    result.delete_candidates = (req, res) ->
        parallel_forEach deleteCandidate, req.body.selection, (err, results) ->
            returnSuccessOrError res, err

    result.emailCandidates = (req, res) ->
        sendEmail = (email, callback) ->
            sendCandidateEmail getFullHostname(req), email, callback
        parallel_forEach sendEmail, req.body.selection, (err, results) ->
            returnSuccessOrError res, err

    result.approveInvitationRequests = (req, res) ->
        approveRequest = (email, callback) ->
            approveInvitationRequest getFullHostname(req), email, callback
        parallel_forEach approveRequest, req.body.selection, (err, results) ->
            returnSuccessOrError res, err

    result.newInvitation = (req, res) ->
        try
            validateNameAndEmail req.body
        catch err
            logger.warn "Invalid invitation request. Error #{err}"
            return res.send 400, err.message

        logger.info "newInvitation: %j", req.body
        auth = app.get 'auth'
        auth.createInvitation req.body, (err, invitation) ->
            return res.send 500, "Failed to create invitation" if err?
            app.get('email').sendInvitation invitation, getFullHostname(req), (err) ->
                if err?
                    auth.deleteInvitation invitation.invite_code, (err) ->
                        logger.error "Failed to delete invitation. Error: #{err}"
                    res.send 500, "Failed to send invitation"
                res.send 200

    result.sendAnnouncement = (req, res) ->
        emailAnnouncement = (email, callback) ->
            logger.info "Retreiving account #{email}"
            async.waterfall [
                (cb) -> app.get('auth').getAccount email, cb
                (user, cb) ->
                    logger.info "Sending email announcement to #{email}. User: %j", user
                    app.get('email').sendAnnouncement user, getFullHostname(req), cb
            ],
            (err, res) ->
                callback(err, res)

        parallel_forEach emailAnnouncement, req.body.selection, (err, results)->
            returnSuccessOrError res, err


    result

validEmailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i
validateNameAndEmail = (body) ->
    throwIfEmpty(val) for val in [body.first_name, body.last_name, body.email]
    throw new Error("Invalid email address") unless body.email.match(validEmailRegex)

throwIfEmpty = (val) ->
    unless val? and val.trim() isnt ''
        throw new Error("Required field is missing or empty")

getFullHostname = (req) ->
    hostname = req.host
    secureport = app.get 'secureport'
    hostname += ":#{secureport}" unless secureport is "443"
    return hostname

parallel_forEach = (fn, collection, callback) ->
    commands = ((do(element) -> (cb) -> fn(element, cb)) for element in collection)
    async.parallel commands, (err, results) ->
        callback(err, results)

returnSuccessOrError = (res, err) ->
    if err?
        return res.send(400, err)
    res.send 200

processCandidateFile = (file, callback) ->
    logger.info "process file: #{file.name}"
    readStream = fs.createReadStream(file.path)
    lineReader = carrier.carry(readStream)
    lineReader.on 'line', (line) ->
        logger.info "Got line #{line}"
        candidate = line.split(',').map((element) -> element.trim())
        if candidate.length > 3
            return callback("Too many elements in line: #{line}")

        logger.info "Candidate: #{candidate}"
        app.get('auth').addCandidate
            first_name: candidate[0]
            last_name: candidate[1]
            email: candidate[2]
            (err) ->
                logger.error "Failed to add candidate #{candidate}" if err?
    lineReader.on 'end', -> callback(null, file.name)

approveInvitationRequest = (host, email, callback) ->
    logger.info "approving invitation request for #{email}"
    auth = app.get 'auth'
    async.waterfall [
        (cb) -> auth.getInvitationRequest email, cb
        (invitation_request, cb) ->
            auth.createInvitation invitation_request, (err, invitaion) ->
                cb(err, invitaion)
        (invitation, cb) ->
            app.get('email').sendInvitation invitation, host, (err) ->
                cb(err, invitation)
        (invitation, cb) ->
            auth.deleteInvitationRequest invitation.email, (err) ->
                if err?
                    logger.info "Failed to delete candidate after sending invitation: %j",
                        invitation
                cb(null, invitation)
        ],
        (err, results) ->
            if err?
                logger.error "Failed to invite candidate. Results: #{results}. Err: #{err}"
            else
                logger.info "Successfully created invitation: %j", results
            callback(err, results)

sendCandidateEmail = (host, email, callback) ->
    logger.info "emailing candidate #{email}"
    auth = app.get 'auth'
    async.waterfall [
        (cb) -> auth.recordCandidateEmail email, cb
        (candidate, email_code, cb) ->
            app.get('email').sendIntroduction candidate, email_code, host, (err) ->
                if err?
                    logger.error "Failed to email candidate #{email}. Error: #{err}"
                    auth.setCandidateLastEmailTime email, candidate.last_email_time, (error) ->
                        logger.error "Failed to reset last_email_time for candidate #{email}".
                        cb(err)
                cb(err, candidate)
        ],
        (err, results) ->
            if err?
                logger.error "Failed to send candidate email to #{email}. Error: #{err}"
            else
                logger.info "Successfully sent candidate email to #{email}"
            callback(err, results)

deleteCandidate = (email, callback) ->
    app.get('auth').deleteCandidate email, callback



