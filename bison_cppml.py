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
"""
import waflib
import re

def options(opt):
    pass

def configure(conf):
    pass


# Extension-based task Generators
@waflib.TaskGen.extension('.ypp')
def preprocess_bison_cppml(self, node):
    outputNode = node.change_ext('.cxx')
    self.create_task('bison_cppml', node, outputNode)
    self.source.append(outputNode)

class bison_cppml(waflib.Task.Task):
    color = "PINK"
    ext_out = ['.cxx']

    def run(self):
        cmd = 'bison %s -o %s' % (self.inputs[0].abspath(), self.outputs[0].abspath())
        workingDirectory = self.outputs[0].parent.abspath()
        self.generator.bld.cmd_and_log(cmd, cwd=workingDirectory, quiet=waflib.Context.STDOUT)

        contents = self.outputs[0].read().replace(".hppml",".hpp_hppml")

        self.outputs[0].write(contents)


