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

path = require 'path'
jade = require 'jade'
stylus = require 'stylus'
juice = require 'juice'
fs = require 'fs'

emailTemplateDir = path.resolve(__dirname, 'email_templates')
imageDir = path.resolve(__dirname, '../public/images')
logoImagePath = path.join(imageDir, 'logo-horizontal.png')

mailer = null
logger = null

module.exports = (app) ->
    mailer = app.get 'mail_client'
    logger = app.get 'logger'

    renderTemplate = (templateName, locals, callback) ->
        jadeFile = path.join(emailTemplateDir, "#{templateName}.jade")
        stylusFile = path.join(emailTemplateDir, "#{templateName}.styl")

        logger.info "Rendering email template: #{jadeFile}"
        jade.renderFile jadeFile, locals, (err, html) ->
            return callback(err) if err?
            fs.readFile stylusFile, 'utf8', (err, styl) ->
                if err?
                    # if there is no .styl file, just serve the rendered html
                    logger.warn "Failed to load stylus file #{stylusFile}:", err
                    return callback(null, html)

                stylus(styl).render (err, css) ->
                    return callback(err) if err?
                    callback null, juice.inlineContent(html, css)

    exports =
        sendAnnouncement: (user, host, callback) ->
            local =
                firs_name: user.first_name
                last_name: user.last_name
                email: user.email
                id: user.id
                host: host
            renderTemplate 'announcement', local, (err, html) ->
                mailOptions =
                    from: mailer.from
                    to: user.email
                    subject: "Ufora Update"
                    html: html
                    generateTextFromHTML: true
                mailer.sendMail mailOptions, (err, response) ->
                    if err?
                        logger.error "Failed to send announcement email to #{user.email}. " +
                            "Error: #{err}"
                        return callback(err)
                    logger.info "Sent announcement email to #{user.email}. Response: %j",
                        response
                    callback null

        sendIntroduction: (candidate, email_code, host, callback) ->
            locals =
                first_name: candidate.first_name
                last_name: candidate.last_name
                email_code: email_code
                host: host
            renderTemplate 'introduction', locals, (err, html) ->
                mailOptions =
                    from: mailer.from
                    to: candidate.email
                    subject: "Introducing Ufora"
                    html: html
                    generateTextFromHTML: true
                mailer.sendMail mailOptions, (err, response) ->
                    if err?
                        logger.error "Failed to send introduction email to #{candidate.email}. " +
                            "Error: #{err}"
                        return callback(err)
                    logger.info "Sent introduction email to #{candidate.email}. Response: %j",
                        response
                    callback null

        sendInvitationRequestConfirmation: (requester, callback) ->
            locals =
                first_name: requester.first_name
                last_name: requester.last_name
            renderTemplate 'invitation_request_confirmation', locals, (err, html) ->
                mailOptions =
                    from: mailer.from
                    to: requester.email
                    subject: "Your Ufora Invitation Request"
                    html: html
                    generateTextFromHTML: true
                mailer.sendMail mailOptions, (err, response) ->
                    if err?
                        logger.info "Error sending invitation request confirmation " +
                            "to #{requester.email}: Error: #{err}"
                        return callback(err)
                    logger.info "Invitation request confirmation sent to #{requester.email}. " +
                        "Response: %j", response
                    callback(null)

        sendInvitation: (invitation, host, callback) ->
            locals =
                first_name: invitation.first_name
                last_name: invitation.last_name
                invite_code: invitation.invite_code
                host: host
            renderTemplate 'invitation', locals, (err, html) ->
                mailOptions =
                    from: mailer.from
                    to: invitation.email
                    subject: "You've been invited to join Ufora"
                    html: html
                    generateTextFromHTML: true
                    attachments: [
                        filename: 'logo-horizontal.png'
                        filePath: logoImagePath
                        cid: 'logo-horizontal'
                    ]
                mailer.sendMail mailOptions, (err, response) ->
                    if err?
                        logger.info "Error sending invitation to #{invitation.email}: Error: #{err}"
                        return callback(err)
                    logger.info "Invitation sent to #{invitation.email}. Response: %j", response
                    callback(null)


