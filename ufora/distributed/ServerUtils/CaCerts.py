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

import sys

def verify(certDomain, targetDomain):
    # this is probably far from perfect but we only care about it matching
    # our own certificates / domains for now..
    cert = certDomain.split('.')
    target = targetDomain.split('.')
    if len(target) != len(cert):
        return False
    
    for ix in range(len(target)):
        if cert[ix] != "*":
            if cert[ix] != target[ix]:
                return False
    return True
            

def osCerts():
    if sys.platform == 'linux2':
        return '/etc/ssl/certs/ca-certificates.crt'


