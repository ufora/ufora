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

import waflib

def cxx_compiler_options(cxx_opts):
    cxx_opts.add_option(
        '--cxx-warnings',
        default='''
                   -Werror
                   -Qunused-arguments
                   -Wno-return-type-c-linkage
                   -Wno-tautological-compare
                   -Wno-dangling-else
                   -Wno-logical-op-parentheses
                   -Wno-deprecated-declarations
                   -Wno-parentheses
                   -Wno-redeclared-class-member
                   -Wno-parentheses-equality
                   -Wno-tautological-undefined-compare
                   -Wno-c++1z-extensions
                   -Wno-#warnings
                   -Wno-unused-value
                   -Wno-tautological-constant-out-of-range-compare
                   -Wno-switch
                   -Wno-string-plus-int
                   -Wno-format
                   -Wno-empty-body
                   ''',
        dest='cxx_warnings',
        help='extra warning flags to pass to C++ compiler')

    cxx_opts.add_option(
        '--cxx-compile-flags',
        default='-pthread -fPIC -std=c++0x',
        dest='cxx_compile_flags',
        help='common flags to pass to C++ compiler')

    cxx_opts.add_option(
        '--cxx-extra-compile-flags',
        default='',
        dest='cxx_extra_compile_flags',
        help='extra flags to pass to C++ compiler')

    cxx_opts.add_option(
        '--cxx-optimize-flag',
        default='-O3 ',
        dest='cxx_optimize_flag',
        help='optimization flag to pass to compiler (-O[0-3])')

    cxx_opts.add_option(
        '--cxx-debug-info-flag',
        default='',
        dest='cxx_debug_flag',
        help='generate debug information? Off by default. Set to -g to add debug info.')


def cxx_defines_options(cxx_opts):
    cxx_opts.add_option(
        '--cxx-user-defines',
        default='__STDC_LIMIT_MACROS __STDC_CONSTANT_MACROS __STDC_FORMAT_MACROS '
                'DONT_GET_PLUGIN_LOADER_OPTION',
        dest='cxx_user_defines',
        help='Additional symbols defined by the user')


def cxx_include_options(cxx_opts):
    def find_numpy():
        try:
            import numpy, os;
            return os.path.dirname(numpy.__file__) + "/core/include"
        except:
            return None

    cxx_opts.add_option(
        '--numpy-include-dir',
        default=find_numpy(),
        dest='cxx_numpy_include',
        help='directory containing numpy headers')

    cxx_opts.add_option(
        '--add-system-include',
        action="append",
        default=['/usr/lib/llvm-3.5/include'],
        dest='cxx_system_includes',
        help='add a directory to the system include path')

    cxx_opts.add_option(
        '--add-user-include',
        action='append',
        default=['ufora', 'cppml/include', 'third_party/'],
        dest='cxx_user_includes',
        help='add a directory to the user include path')


def cxx_link_flags_options(cxx_opts):
    cxx_opts.add_option(
        '--cxx-link-flags',
        default='-pthread',
        dest='cxx_link_flags',
        help='extra flags to pass to C++ linker')
    cxx_opts.add_option(
        '--cxx-rpath',
        default='$ORIGIN',
        dest='cxx_rpath',
        help='define a cxx rpath')


def cxx_libs_options(cxx_opts):
    cxx_opts.add_option(
        '--add-library-dir',
        action='append',
        default=['/usr/lib/llvm-3.5/lib'],
        dest='link_lib_dirs',
        help='add a directory to the library path for linking')

    cxx_opts.add_option(
        '--add-library',
        action='append',
        default=[],
        dest='link_libs',
        help='add a library against which to link')


def options(opt):
    cxx_opts = opt.add_option_group('C++ Options')
    cxx_compiler_options(cxx_opts)
    cxx_include_options(cxx_opts)
    cxx_link_flags_options(cxx_opts)
    cxx_libs_options(cxx_opts)
    cxx_defines_options(cxx_opts)



@waflib.Configure.conf
def cxx_flags(conf):
    conf.env.append_unique(
        'CXXFLAGS',
        conf.options.cxx_warnings.split() + \
        conf.options.cxx_compile_flags.split() + \
        conf.options.cxx_extra_compile_flags.split() + \
        conf.options.cxx_optimize_flag.split() + \
        conf.options.cxx_debug_flag.split()
        )
    for opt in dir(conf.options):
        if opt.endswith('_cxxflags') and getattr(conf.options, opt) is not None:
            conf.env.append_unique('CXXFLAGS', getattr(conf.options, opt).split())

@waflib.Configure.conf
def cxx_includes(conf):
    conf.env.append_unique(
        "SYS_INCLUDES",
        conf.options.cxx_system_includes + \
        conf.options.cxx_user_includes
        )
    conf.env.SYS_INCLUDES.extend(
        (getattr(conf.options, opt)
         for opt in dir(conf.options)
         if opt.endswith('_include') and getattr(conf.options, opt) is not None)
        )

@waflib.Configure.conf
def cxx_libs(conf):
    conf.env.LIB_DIRS = conf.options.link_lib_dirs
    conf.env.LIBS = conf.options.link_libs
    conf.env.LIBS.extend(
        (getattr(conf.options, opt)
         for opt in dir(conf.options)
         if opt.endswith('_lib'))
        )


@waflib.Configure.conf
def cxx_common_defines(conf):
    conf.env.append_unique(
        'CXXDEFINES',
        conf.options.cxx_user_defines.split()
        )

@waflib.Configure.conf
def cxx_link(conf):
    conf.env.append_unique('LINKFLAGS', conf.options.cxx_link_flags.split())


def configure(conf):
    cxx_flags(conf)
    cxx_includes(conf)
    cxx_libs(conf)
    cxx_common_defines(conf)
    cxx_link(conf)

    conf.env.append_unique('RPATH', conf.options.cxx_rpath.split())
