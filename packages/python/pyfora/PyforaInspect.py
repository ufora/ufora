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

# This is a copy of inspect.py from python 2.7 with a mod in findsource
# to throw when there are multiple candidates when looking for a class
# which was implemented as a best-effort.
# -*- coding: iso-8859-1 -*-
"""Get useful information from live Python objects.

This module slightly modifies the behavior of the inspect.py module,
which takes a best-effort approach to returning the source or sourcelines
of objects that represent classes. Our approach is to raise a
PyforaInspectError exception if we cannot determine unequivocally which
source corresponds to the queried object.

This module implements a modified version of the 'findsource' function
provided by inspect, and it provides the entry points that can reach this
function unmodified. These are: getcomments, getsourcelines, getsource,
getframeinfo, getouterframes, getinnerframes, stack, and trace.

Here are some of the useful functions provided by this module which are
directly imported from the inspect module:

    ismodule(), isclass(), ismethod(), isfunction(), isgeneratorfunction(),
        isgenerator(), istraceback(), isframe(), iscode(), isbuiltin(),
        isroutine() - check object types
    getmembers() - get members of an object that satisfy a given condition

    getfile() - find an object's source code
    getdoc() - get documentation on an object
    getmodule() - determine the module that an object came from
    getclasstree() - arrange classes so as to represent their hierarchy

    getargspec(), getargvalues(), getcallargs() - get info about function arguments
    formatargspec(), formatargvalues() - format an argument spec
    currentframe() - get the current stack frame
"""

# This module is in the public domain.  No warranties.

__author__ = 'Alexandros Tzannes <atzannes@gmail.com>'
__date__ = '8 Oct 2015'

import imp
import inspect
import linecache
import os
import pyfora.StdinCache as StdinCache
import re
import string
import sys

# Importing the following functions so that this module can act as a drop-in
# replacement for inspect, which it modifies
from inspect import ismodule, isclass, ismethod, ismethoddescriptor, \
    isdatadescriptor, ismemberdescriptor, isgetsetdescriptor, isfunction, \
    isgeneratorfunction, isgenerator, istraceback, isframe, iscode, isbuiltin, \
    isroutine, isabstract, getmembers, classify_class_attrs, getmro,\
    indentsize, getdoc, cleandoc, getmoduleinfo, getmodulename, \
    getabsfile, getmodule, getblock, walktree, getclasstree, \
    getargs, getargspec, getargvalues, joinseq, strseq, formatargspec, \
    formatargvalues, getcallargs, getlineno

from collections import namedtuple

class PyforaInspectError(Exception):
    pass

# ---------------- modified code
#cache to hold paths that we've determined are already present/not present in
#the system. This prevents python from hitting os.path.exists over and over,
#which can be slow.
pathExistsOnDiskCache_ = {}
linesCache_ = {}

def getlines(path):
    """return a list of lines for a given path.

    This override is also careful to map "<stdin>" to the full contents of
    the readline buffer.
    """
    if path == "<stdin>":
        return StdinCache.singleton().refreshFromReadline().getlines()

    if path in linesCache_:
        return linesCache_[path]

    if path not in pathExistsOnDiskCache_:
        pathExistsOnDiskCache_[path] = os.path.exists(path)

    if pathExistsOnDiskCache_[path]:
        with open(path, "r") as f:
            linesCache_[path] = f.readlines()
        return linesCache_[path]
    elif path in linecache.cache:
        return linecache.cache[path][2]
    else:
        return None

def getfile(pyObject):
    try:
        return inspect.getfile(pyObject)
    except TypeError:
        if isclass(pyObject):
            return _try_getfile_class(pyObject)
        raise

def _try_getfile_class(pyObject):
    members = getmembers(
        pyObject,
        lambda _: ismethod(_) or isfunction(_)
        )

    if len(members) == 0:
        raise PyforaInspectError(
            "can't get source code for class %s" % pyObject
            )

    # members is a list of tuples: (name, func)
    elt0 = members[0][1]

    if isfunction(elt0):
        func = elt0
    else:
        # must be a method
        func = elt0.im_func

    return inspect.getfile(func)
        
def getsourcefile(pyObject):
    """Return the filename that can be used to locate an object's source.
    Return None if no way can be identified to get the source.
    """
    filename = getfile(pyObject)

    if filename == "<stdin>":
        return filename

    if string.lower(filename[-4:]) in ('.pyc', '.pyo'):
        filename = filename[:-4] + '.py'
    for suffix, mode, _ in imp.get_suffixes():
        if 'b' in mode and string.lower(filename[-len(suffix):]) == suffix:
            # Looks like a binary file.  We want to only return a text file.
            return None

    if filename not in pathExistsOnDiskCache_:
        pathExistsOnDiskCache_[filename] = os.path.exists(filename)

    if pathExistsOnDiskCache_[filename]:
        return filename

    # only return a non-existent filename if the module has a PEP 302 loader
    if hasattr(getmodule(pyObject, filename), '__loader__'):
        return filename
    # or it is in the linecache
    if filename in linecache.cache:
        return filename

def findsource(pyObject):
    """Return the entire source file and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of all the lines
    in the file and the line number indexes a line in that list.  An IOError
    is raised if the source code cannot be retrieved."""

    pyFile = getfile(pyObject)
    sourcefile = getsourcefile(pyObject)

    if not sourcefile and pyFile[:1] + pyFile[-1:] != '<>':
        raise IOError('source code not available')

    pyFile = sourcefile if sourcefile else file

    lines = getlines(pyFile)
    if not lines:
        raise IOError('could not get source code')

    if ismodule(pyObject):
        return lines, 0

    if isclass(pyObject):
        name = pyObject.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        # find all matching class definitions and if more than one
        # is found, raise a PyforaInspectError
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                # add to candidate list
                candidates.append(i)
        if not candidates:
            raise IOError('could not find class definition for %s' % pyObject)
        elif len(candidates) > 1:
            raise PyforaInspectError('could not find class unequivocally: class ' + name)
        else:
            # classes may have decorators and the decorator is considered part
            # of the class definition
            lnum = candidates[0]
            pat = re.compile(r'^(\s*)@\w+')
            while lnum > 0 and pat.match(lines[lnum-1]):
                lnum -= 1
            return lines, lnum

    if ismethod(pyObject):
        pyObject = pyObject.im_func
    if isfunction(pyObject):
        pyObject = pyObject.func_code
    if istraceback(pyObject):
        pyObject = pyObject.tb_frame
    if isframe(pyObject):
        pyObject = pyObject.f_code
    if iscode(pyObject):
        if pyFile == "<stdin>":
            #the "co_firstlineno" variable is wrong in this case.
            #we need to find the actual line number
            lnum = StdinCache.singleton().refreshFromReadline().findCodeLineNumberWithinStdin(pyObject)
        else:
            if not hasattr(pyObject, 'co_firstlineno'):
                raise IOError('could not find function definition')
            lnum = pyObject.co_firstlineno - 1
        pat = re.compile(r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)')
        while lnum > 0:
            if pat.match(lines[lnum]): break
            lnum = lnum - 1
        return lines, lnum
    raise IOError('could not find code object')

# ---------------- unmodified code (from inspect.py in the python2.7 distribution)
def getcomments(pyObject):
    """Get lines of comments immediately preceding an object's source code.

    Returns None when source can't be found.
    """
    try:
        lines, lnum = findsource(pyObject)
    except (IOError, TypeError):
        return None

    if ismodule(pyObject):
        # Look for a comment block at the top of the file.
        start = 0
        if lines and lines[0][:2] == '#!': start = 1
        while start < len(lines) and string.strip(lines[start]) in ('', '#'):
            start = start + 1
        if start < len(lines) and lines[start][:1] == '#':
            comments = []
            end = start
            while end < len(lines) and lines[end][:1] == '#':
                comments.append(string.expandtabs(lines[end]))
                end = end + 1
            return string.join(comments, '')

    # Look for a preceding block of comments at the same indentation.
    elif lnum > 0:
        indent = indentsize(lines[lnum])
        end = lnum - 1
        if end >= 0 and string.lstrip(lines[end])[:1] == '#' and \
            indentsize(lines[end]) == indent:
            comments = [string.lstrip(string.expandtabs(lines[end]))]
            if end > 0:
                end = end - 1
                comment = string.lstrip(string.expandtabs(lines[end]))
                while comment[:1] == '#' and indentsize(lines[end]) == indent:
                    comments[:0] = [comment]
                    end = end - 1
                    if end < 0: break
                    comment = string.lstrip(string.expandtabs(lines[end]))
            while comments and string.strip(comments[0]) == '#':
                comments[:1] = []
            while comments and string.strip(comments[-1]) == '#':
                comments[-1:] = []
            return string.join(comments, '')

def getsourcelines(pyObject):
    """Return a list of source lines and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of the lines
    corresponding to the object and the line number indicates where in the
    original source file the first line of code was found.  An IOError is
    raised if the source code cannot be retrieved."""
    lines, lnum = findsource(pyObject)

    if ismodule(pyObject): return lines, 0
    else: return getblock(lines[lnum:]), lnum + 1

def getsource(pyObject):
    """Return the text of the source code for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a single string.  An
    IOError is raised if the source code cannot be retrieved."""
    lines, _ = getsourcelines(pyObject)
    return string.join(lines, '')

Traceback = namedtuple('Traceback', 'filename lineno function code_context index')

def getframeinfo(frame, context=1):
    """Get information about a frame or traceback object.

    A tuple of five things is returned: the filename, the line number of
    the current line, the function name, a list of lines of context from
    the source code, and the index of the current line within that list.
    The optional second argument specifies the number of lines of context
    to return, which are centered around the current line."""
    if istraceback(frame):
        lineno = frame.tb_lineno
        frame = frame.tb_frame
    else:
        lineno = frame.f_lineno

    if not isframe(frame):
        raise TypeError('{!r} is not a frame or traceback object'.format(frame))

    filename = getsourcefile(frame) or getfile(frame)

    lines = None
    if filename == "<stdin>":
        lineno = StdinCache.singleton().refreshFromReadline().findCodeLineNumberWithinStdin(frame.f_code) + 1
        lines = StdinCache.singleton().getlines()


    if context > 0:
        start = lineno - 1 - context//2
        try:
            if lines is None:
                lines, _ = findsource(frame)
        except IOError:
            if lines is None:
                lines = index = None
        else:
            start = max(start, 1)
            start = max(0, min(start, len(lines) - context))
            lines = lines[start:start+context]
            index = lineno - 1 - start
    else:
        lines = index = None

    return Traceback(filename, lineno, frame.f_code.co_name, lines, index)

def getouterframes(frame, context=1):
    """Get a list of records for a frame and all higher (calling) frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context."""
    framelist = []
    while frame:
        framelist.append((frame,) + getframeinfo(frame, context))
        frame = frame.f_back
    return framelist

def getinnerframes(tb, context=1):
    """Get a list of records for a traceback's frame and all lower frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context."""
    framelist = []
    while tb:
        framelist.append((tb.tb_frame,) + getframeinfo(tb, context))
        tb = tb.tb_next
    return framelist

if hasattr(sys, '_getframe'):
    currentframe = sys._getframe
else:
    currentframe = lambda _=None: None

def stack(context=1):
    """Return a list of records for the stack above the caller's frame."""
    return getouterframes(sys._getframe(1), context)

def trace(context=1):
    """Return a list of records for the stack below the current exception."""
    return getinnerframes(sys.exc_info()[2], context)

