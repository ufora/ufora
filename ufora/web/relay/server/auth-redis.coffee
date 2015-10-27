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
node_redis = require 'redis'
crypto = require 'crypto'
string = require 'string'
bcrypt = require 'bcrypt'

redis = null
logger = null
currentTosVersion = null
userDefaults = null

userKey = (id) ->
    return "user:#{id}"

retrieveUser = (id, done) ->
    loadUserDefaults (defaults) ->
        redis.hgetall userKey(id), (err, user) ->
            if err?
                logger.error "Failed to retrieve user #{id}. #{err}"
                return done(err)

            return done(null, null) unless user?
            user.is_admin = -> user.role is 'admin'
            user[key] = value for key, value of defaults when not user[key]?
            user.tos = user.tos if user.eula? and not user.tos?
            done null, user

loadUserDefaults = (done) ->
    return done(userDefaults) if userDefaults?
    redis.hgetall "config:user_defaults", (err, defaults) ->
        unless defaults?
            logger.warn "No configuration found for default user settings (config:user_defaults)"
            defaults =
                visible: '1'
                defaultBootableMachineSize: '8'
                maxBootableMachines: '4'
                machineTtl: '3600'
                showRemainingTime: '1'
        userDefaults = defaults
        done(userDefaults)

module.exports.authenticate = (credentials, done) ->
    logger.info "authenticating #{credentials.user}"
    retrieveUser credentials.user, (err, user) ->
        logger.info "received retrieveUser callback for #{credentials.user}. #{err}"
        return done(null, false) if err? or not user?
        unless user.password?
            return done(new Error("User record has no password: #{credentials.user}"), false)
        bcrypt.compare credentials.password, user.password, (err, match) ->
            done null, if match then user else null

module.exports.serializeUser = (user, done) ->
    return done(new Error("Missing user id"), false) unless user.id?
    done null, user.email

module.exports.deserializeUser = (email, done) ->
    retrieveUser email, (err, user) ->
        return done(err) if err?
        if user?
            user.acceptedTos = ->
                console.info 'updating TOS for', email
                redis.hmset userKey(email), 'tos', currentTosVersion, 'tosAcceptTime', Date()
        done null, user

module.exports.initialize = (app) ->
    logger = app.get 'logger'
    currentTosVersion = app.get 'tosVersion'
    redis = node_redis.createClient()
    redis.on 'error', (err) ->
        logger.error 'Error in Redis client:', err

module.exports.listUsers = (count, from, callback) ->
    getHashesByPrefix 'user:*', count, from, callback

module.exports.listPendingInvitations = (count, from , callback) ->
    getHashesByPrefix 'invitation:*', count, from, callback

module.exports.listInvitationRequests = (count, from , callback) ->
    getHashesByPrefix 'invitation_request:*', count, from, callback

module.exports.listCandidates = (count, from , callback) ->
    getHashesByPrefix 'candidate:*', count, from, callback

getHashesByPrefix = (prefix, count, from, callback) ->
    from = 0 unless from?
    redis.keys prefix, (err, keys) ->
        return callback(err) if err?
        count = keys.length - from unless count?
        multi = redis.multi()
        multi.hgetall(key.toString()) for key in keys[from...from+count]
        multi.exec callback

module.exports.addCandidate = (candidate, callback) ->
    unless candidate.first_name? and candidate.last_name? and candidate.email?
        return callback "missing required fields"
    candidate.created_time = new Date().toJSON()
    candidate.last_email_time = ""
    key = "candidate:#{candidate.email}"
    redis.exists key, (err, exists) ->
        return callback(err) if err?
        return callback(
            status: 400
            message:"Candidate with this email already exists"
            ) if exists
        redis.hmset key, candidate, callback

module.exports.deleteCandidate = (email, callback) ->
    redis.del "candidate:#{email}", callback

module.exports.recordCandidateEmail = (email, callback) ->
    email_code = crypto.randomBytes(10).toString('hex')
    multi = redis.multi()
    multi.hset "candidate:#{email}", "last_email_time", new Date().toJSON()
    multi.set "candidate_email:#{email_code}", "candidate:#{email}"
    multi.hgetall "candidate:#{email}"
    multi.exec (err, replies) ->
        return callback(err) if err?
        callback(null, replies[2], email_code)

module.exports.candidateFromEmailCode = (code, callback) ->
    async.waterfall [
        (cb) -> redis.get "candidate_email:#{code}", cb
        (candidate_key, cb) -> redis.hgetall candidate_key, cb
        ],
        callback

module.exports.deleteCandidateEmailCode = (code, callback) ->
    redis.del "candidate_email:#{code}", callback

module.exports.getInvitationRequest = (email, callback) ->
    redis.hgetall "invitation_request:#{email}", callback

module.exports.addInvitationRequest = (request, callback) ->
    unless request.first_name? and request.last_name? and request.email?
        return callback("Missing required fields")
    request.request_time = new Date().toJSON()
    key = "invitation_request:#{request.email}"
    redis.exists key, (err, exists) ->
        return callback(err) if err?
        return callback(
            status: 400
            message: "An invitation for this email address already exists"
            ) if exists
        redis.hmset key, request, callback

module.exports.deleteInvitationRequest = (email, callback) ->
    redis.del "invitation_request:#{email}", callback

module.exports.createInvitation = (invitation_request, callback) ->
    invitation =
        first_name: invitation_request.first_name
        last_name: invitation_request.last_name
        email: invitation_request.email
        invite_time: new Date().toJSON()
        invite_code: crypto.randomBytes(10).toString('hex')
        invitation_count: "1"
    redis.hmset "invitation:#{invitation.invite_code}", invitation, (err, reply) ->
        callback err, invitation

module.exports.getInvitation = (invite_code, callback) ->
    redis.hgetall "invitation:#{invite_code}", callback

module.exports.deleteInvitation = (invite_code, callback) ->
    redis.del "invitation:#{invite_code}", callback

module.exports.getAccount = (email, callback) ->
    redis.hgetall "user:#{email}", callback

module.exports.createAccount = ({first_name, last_name, email, id, password}, callback) ->
    redis.exists "user:#{email}", (err, exists) ->
        return callback(err) if err?
        return callback({status: 400, message: "Account already exists"}) if exists
        bcrypt.hash password, 10, (err, passwordHash) ->
            account =
                id: id
                first_name: first_name
                last_name: last_name
                email: email
                password: passwordHash
                creation_time: new Date().toJSON()
                tos: 0
                role: "user"
            redis.hmset "user:#{email}", account, callback


