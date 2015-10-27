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

passport = require 'passport'

authStrategy = null
logger = require './logging'

currentTosVersion = null
clusterType = 'public'

LocalStrategy = require('passport-local').Strategy
passport.use new LocalStrategy((username, password, done) ->
    try
        credentials =
            user: username
            password: password
        authStrategy.authenticate credentials, (err, user) ->
            user ?= false
            return done(err) if err?
            if user
                logger.info "User #{username} successfully logged in."
                return done null, user
            else
                return done null, null,
                    message: 'Unknown user or incorrect password'
    catch err
        return done err
    )

module.exports.initialize = (app) ->
    currentTosVersion = app.get 'tosVersion'
    clusterType = app.get 'clustertype'
    authStrategy = require "./#{app.get('authStrategy')}"
    authStrategy.initialize app
    module.exports[key] = val for key, val of authStrategy when key isnt 'initialize'

    passport.serializeUser module.exports.serializeUser
    passport.deserializeUser module.exports.deserializeUser
    app.use passport.initialize()
    app.use passport.session()


unrestrictedPages = [/^\/login/, /^\/logout/, /^\/signup/, /^\/legal\/.*/]
module.exports.redirectToLogin = (req, res, next) ->
    for regex in unrestrictedPages
        if req.url.match(regex)
            return next()

    unless req.user?
        return res.redirect "/login?redirect=#{encodeURIComponent(req.url)}"

    if req.url.match(/^\/admin/) and not req.user.is_admin()
        return res.send 401, "Unauthorized"

    if req.url.match(/^\/tos/)
        return next()

    if req.user.id == 'test'
        return next()

    unless clusterType isnt 'public' or req.user?.tos is currentTosVersion
        return res.redirect "/tos?redirect=#{encodeURIComponent(req.url)}"
    next()

module.exports.authenticate_request = (req, res, next) ->
    module.exports.authenticate_without_redirect req, res, next, (err, user, message) ->
        return next(err) if err?
        unless user?
            req.flash 'error', message
            return res.redirect '/login'
        redirectTo = req.query.redirect ? '/'
        return res.redirect redirectTo

module.exports.authenticate_without_redirect = (req, res, next, done) ->
    auth = passport.authenticate 'local', (err, user, info) ->
        user ?= false
        return done(err) if err?
        return done(null, null, info.message) unless user
        req.logIn user, (err) ->
            if not err? and user?
                res.setHeader('x_ufora_login_success', 'true')

            done(err, user)
    auth req, res, next

module.exports.authenticate_request_if_present = (req, res, next) ->
    if req.query.username? and req.query.password?
        module.exports.authenticate_request req, res, next
        return
    next()

