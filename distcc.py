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

#! /usr/bin/env python2
# encoding: utf-8

"""
This file implements a WAF tool that adds support for DISTCC.

If it detects DISTCC is installed, it wraps the CXX and CC programs with it.
"""
import commands
import os

def configure(conf):
    cxx = conf.env['CXX']
    cc = conf.env['CC']

    distcc = conf.find_program('distcc', var='DISTCC', mandatory=False)
    ccache = conf.find_program('ccache', var='CCACHE', mandatory=False)

    if ccache:
        cxx = [ccache] + cxx
        cc = [ccache] + cc
    elif distcc:
        cxx = [distcc] + cxx
        cc = [distcc] + cc

    conf.env['CXX'] = cxx
    conf.env['CC'] = cc

def build(bld):
    os.environ['CCACHE_SLOPPINESS'] = 'include_file_mtime' # Headers in different repos may have different mtimes
    os.environ['CCACHE_BASEDIR'] = bld.path.get_src().abspath() # This makes ccache more intelligent about paths
    os.environ['CCACHE_COMPRESS'] = 'true'
    if os.path.isdir('/ccache'):
        # Needed to share ccache folders
        os.environ['CCACHE_UMASK'] = '000'
        os.environ['CCACHE_DIR'] = '/ccache'
    if bld.env.CCACHE and bld.env.DISTCC:
        os.environ['CCACHE_PREFIX'] = bld.env.DISTCC
    if bld.env.CCACHE:
        bld.nocache = True
    if bld.env.DISTCC:
        jobCount = int(commands.getoutput('distcc -j'))

        # For our product, jobCount is WAY too high, so reduce it
        bld.jobs = int(jobCount / 4)

