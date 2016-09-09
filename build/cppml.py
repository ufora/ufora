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
This file implements a WAF tool that adds support for CPPML.
It performs preprocessing for all .cppml, .hppml, .cpp, and .hpp file.

It outputs .cxx files and .hpp files in which all CPPML constructs have been
expanded to C++ code and all references to .hppml files have been replaced
with references to the corresponding .hpp files.

The resulting .cxx files can then be passed to a C++ compiler using the
standard WAF mechanisms.
"""
import os.path
import waflib

def configure(conf):
    conf.env['CPPML'] = conf.find_program('cppml', var='CPPML', mandatory=False)
    conf.env['CPPMLFLAGS'] = '--guarded-preamble'

# Extension-based task Generators
@waflib.TaskGen.extension('.cppml')
def preprocess_cppml(self, node):
    outputNode = node.change_ext('.cppmli')
    self.create_task('addLineNumbersTask', node, outputNode)
    self.source.append(outputNode)

@waflib.TaskGen.extension('.cppmli')
def preprocess_cppml(self, node):
    outputNode = node.change_ext('.cxx')
    self.create_task('cppml', node, outputNode)
    self.source.append(outputNode)

@waflib.TaskGen.extension('.hppml')
def preprocess_cppml(self, node):
    outputNode = node.change_ext('.hppmli')
    self.create_task('addLineNumbersTask', node, outputNode)
    self.source.append(outputNode)

@waflib.TaskGen.extension('.hppmli')
def preprocess_cppml(self, node):
    outputNode = node.change_ext('.hpp_hppml')
    self.create_task('cppml', node, outputNode)

@waflib.TaskGen.extension('.hpp_hppml')
def preprocess_cppml(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.hpp')
def preprocess_cppml(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.h')
def preprocess_cppml_h(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.c')
def preprocess_copy_c_files(self, node):
    outputNode = node.get_bld()
    self.create_task('c', node, outputNode)

@waflib.TaskGen.extension('.inc')
def preprocess_cppml_h(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.inl')
def preprocess_cppml_h(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.gen')
def preprocess_cppml_h(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.def')
def preprocess_cppml_h(self, node):
    outputNode = node.get_bld()
    self.create_task('cpp', node, outputNode)

@waflib.TaskGen.extension('.cpp')
def preprocess_cppml(self, node):
    if node.is_src():
        outputNode = node.change_ext('.cxx')
        self.create_task('cpp', node, outputNode)
        self.source.append(outputNode)

class addLineNumbersTask(waflib.Task.Task):
    color = "PINK"
    ext_out = ['.cppmli', '.hppmli']

    def run(self):
        output = addGCCLineNumberDirective(
            self.inputs[0].read(),
            # Use relative paths to keep files identical between build directories
            self.inputs[0].bldpath(),
            self.env.isCoverageBuild
            )
        self.outputs[0].parent.mkdir()
        self.outputs[0].write(output)



def run_on_signature_error(task):
    try:
        task.signature() # ensure that files are scanned - unfortunately
    except:
        return waflib.Task.RUN_ME

    return waflib.Task.Task.runnable_status(task)


class cppml(waflib.Task.Task):
    """
    A WAF Task that processes passes input files through the cppml tool.

    In addition to running files through the tool, it also replaces .hppml
    includes with the corresponding .hpp references.
    It then wraps the entire output file in an additional include guard because
    the cppml tool adds code at the bottom of the source file, outside any include
    guards that may have existed in the original .hppml file.
    """
    color = 'BLUE'
    ext_out = ['.cxx', '.hpp', '.hpp_hppml']
    vars = ['CPPMLFLAGS']
    runnable_status = run_on_signature_error

    def run(self):
        cmd = '%s %s %s' % (self.env.CPPML, self.inputs[0].abspath(), self.env.CPPMLFLAGS)
        workingDirectory = self.outputs[0].parent.abspath()
        output = self.generator.bld.cmd_and_log(cmd, cwd=workingDirectory, quiet=waflib.Context.STDOUT)
        output = replaceHppmlIncludes(output)

        output = self.wrapWithIncludeGuard(output, self.outputs[0])
        self.outputs[0].write(output)

    def scan(self):
        deps = []
        cppml = self.generator.bld.path.find_resource('tools/cppml')
        if cppml:
            deps.append(cppml)

        return (deps, None)

    def wrapWithIncludeGuard(self, content, outputNode):
        includeGuard = self.sanitizedFilenameIncludeGuard(outputNode.abspath())
        return "#ifndef %s\n#define %s\n%s\n\n#endif\n" % (includeGuard, includeGuard, content)

    def sanitizedFilenameIncludeGuard(self, absFileName):
        """produce a string that matches the filename, but that's appropriate for use in a #include"""
        # Use relative path to ensure files are identical across build directories
        relFileName = os.path.relpath(absFileName)
        return "__CPPML_TRANSFORMED_" + "".join(['_' if not x.isalnum() else x for x in relFileName])

class cpp(waflib.Task.Task):
    color = "BLUE"
    ext_out = ['.cxx', '.hpp', '.hpp_hppml', '.h', '.inc', '.gen', '.def']

    def run(self):
        output = replaceHppmlIncludes(self.inputs[0].read())

        self.outputs[0].parent.mkdir()
        self.outputs[0].write(output)

class c(waflib.Task.Task):
    color = "BLUE"
    ext_out = ['.c']

    def run(self):
        output = self.inputs[0].read()

        self.outputs[0].parent.mkdir()
        self.outputs[0].write(output)

def replaceHppmlIncludes(content):
    lines = content.split("\n")
    newContent = []

    for l in lines:
        if l.strip().startswith("#include"):
            newContent.append(l.replace(".hppml", ".hpp_hppml"))
        else:
            newContent.append(l)
    return "\n".join(newContent)

def addGCCLineNumberDirective(contents, path, isCoverageBuild):
    if isCoverageBuild:
        # we don't want to mess with line numbers when measuring code coverage
        return contents
    else:
        contents = contents.split("\n")
        lineNumber = 1
        outContents = []
        lastLineEndedInBackslash = False
        for line in contents:
            if not lastLineEndedInBackslash:
                outContents.append('#line %d "%s"' % (lineNumber, path))
            outContents.append(line)
            lastLineEndedInBackslash = line.endswith("\\")
            lineNumber += 1
        return "\n".join(outContents)

