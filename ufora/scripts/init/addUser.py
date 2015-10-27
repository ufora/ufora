#!/usr/bin/env python

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

import argparse
import bcrypt
import getpass
import re
import redis
import sys

def getUserRecord(options):
    user = {}
    user['email'] = options.email or requiredInput('Email address')
    user['password'] = hashPassword(options.password or readPassword())
    user['first_name'] = options.first_name or requiredInput('First name')
    user['last_name'] = options.last_name or requiredInput('Last name')

    for key, value in user.iteritems():
        user[key] = value.strip()
        if not user[key]:
            raise Exception("%s cannot be blank")

    user['role'] = 'user'
    user['visible'] = 1
    user['id'] = emailToUserId(user['email'])
    user['eula'] = 1
    return user

def hashPassword(password):
    return bcrypt.hashpw(password.strip(), generateSalt(10))

def generateSalt(rounds):
    if int(bcrypt.__version__[0]) >= 2:
        return bcrypt.gensalt(rounds, '2a')
    else:
        return bcrypt.gensalt(rounds)

def readPassword():
    password = getPassword()
    while not password:
        print "Password cannot be blank."
        password = getPassword()
    repassword = getpass.getpass('Password (repeat): ')
    if password != repassword:
        raise Exception("Passwords don't match.")
    return password

def getPassword(label='Password'):
    return getpass.getpass('%s: ' % label).strip()

def requiredInput(label):
    value = raw_input("%s: " % label).strip()
    while not value:
        print "%s cannot be blank." % label
        value = raw_input("%s: " % label).strip()
    return value

def emailToUserId(email):
    userId = re.sub(r'\W', '', email)
    userId = re.sub(r'^\d+', '', userId)
    return userId

def writeUserRecord(user):
    r = redis.StrictRedis()
    r.hmset('user:%s' % user['email'], user)

def userExists(user):
    r = redis.StrictRedis()
    return len(r.keys('user:%s' % user['email'])) > 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-e', '--email',
            help="User's email address. This is also the login name."
            )
    parser.add_argument(
            '-p', '--password',
            help="The password assigned to the new user."
            )
    parser.add_argument(
            '-f', '--first-name',
            help="User's first name"
            )
    parser.add_argument(
            '-l', '--last-name',
            help="User's last name"
            )
    parser.add_argument(
            '-r', '--replace-existing',
            help="Set this switch to overwrite users that already exist.",
            action='store_true'
            )
    options = parser.parse_args()

    try:
        user = getUserRecord(options)
        print ""
    except Exception as e:
        print "Error: ", e
        return 2

    try:
        if not options.replace_existing and userExists(user):
            print "Error: A user with this email address already exists."
            print "       Use the -r (--replace-existing) switch to overwrite."
            return 1

        writeUserRecord(user)
    except redis.exceptions.ConnectionError as e:
        print "Error: Unable to connecto to local redis-server. Please make sure redis-server is installed and running."
        print e
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

