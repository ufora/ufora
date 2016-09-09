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

import ufora.native.Control as ControlNative
import logging

ControlInstance = ControlNative.ControlInstance

funtype = type(lambda:0)

def deLambda(x, *args):
    if isinstance(x, funtype):
        return x(*args)
    return x

def isLambdaWithOneArgument(x):
    """Returns whether 'x' is a lambda function containing a single argument"""
    try:
        return x.func_code.co_argcount == 1
    except AttributeError:
        return False

def lambdaFunctionToString(x):
    """Convert a function to a string containing a filename and line number."""
    try:
        return "%s::%s. %s" % (
            x.func_code.co_filename,
            x.func_code.co_firstlineno,
            x
            )
    except Exception as e:
        return "<ERROR IN lambdaFunctionToString on %s>" % x


Control = ControlNative.Control
ControlInstance = ControlNative.ControlInstance

def generated(f, forceCache=False, identifier=''):
    return ControlNative.Generated(f, forceCache, identifier)

empty = ControlNative.Empty

root = ControlNative.createCache

def overlayGenerated(keyGeneratorFunction, keyToControlFunction, maxKeysToCache=0):
    """Overlay a group of controls ontop of each other, tracking differences
    in the group of controls and only regenerating them as necessary.

    keyGeneratorFunction: a function taking no arguments that produces a list of
        control keys.  If the list changes, we rebuild the control list.
    keyToControlFunction: a function that takes a control 'key' and produces
        an actual control object to display.
    maxKeysToCache: how many keys should we keep around in the background? Cached
        keys speed up the update cycle, but can cause us to update unnecessary
        properties in the computed graph.
    """
    def upRule(prefs):
        if len(prefs) == 0:
            return (0,0)
        return (max([p[0] for p in prefs]), max([p[1] for p in prefs]))

    def downRule(avail, prefs):
        return [(avail, (0,0)) for p in prefs]

    return ControlNative.Layout(
        ControlNative.ArbitraryLayout(upRule, downRule),
        keyGeneratorFunction,
        keyToControlFunction,
        maxKeysToCache
        )

def exceptionText(*args):
    logging.info("Exception in control tree: %s", args)
    return empty()

