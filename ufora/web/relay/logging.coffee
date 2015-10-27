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


# Custom logging class to replace 'console' for all logging tasks.
#
# Bound as the variable 'logging' to the 'window' object with the function 'resetLogging' found in
# build/requirejs-wrapper.frag
class Logger
  constructor: (config) ->
    @config = config

  debug: () =>
    if @config.logging_levels.debug
      console.debug.apply console, arguments

  info: () =>
    if @config.logging_levels.info
      console.info.apply console, arguments

  log: () =>
    if @config.logging_levels.log
      console.log.apply console, arguments

  warn: () =>
    if @config.logging_levels.warn
      console.warn.apply console, arguments

  error: () =>
    if @config.logging_levels.error
      console.error.apply console, arguments

  critical: () =>
    console.error.apply console, arguments

  test: () =>
    console.log.apply console, arguments


if module?
  module.exports = Logger
else
  logging = null

  window.resetLogging = () ->
    window.logging = new Logger Config
    logging = window.logging

  window.logging = new Logger Config
  logging = window.logging


