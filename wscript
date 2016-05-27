#!/usr/bin/env python2
# encoding: utf-8

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

import itertools
import os
from waflib import Build, Utils, TaskGen
import sys

ENABLE_FORTRAN = (sys.platform != "darwin")

out = '.build' if 'WAF_OUT' not in os.environ else os.environ['WAF_OUT']

import waflib.Tools.c_preproc as c_preproc
c_preproc.strict_quotes = True

def options(opt):
    opt.load('compiler_cxx')
    opt.load('compiler_c')
    opt.load('cxx')
    opt.load('compiler_fc')
    opt.load('configure_cpp', tooldir='build')
    opt.load('bison_cppml', tooldir='build')
    opt.load('ocaml', tooldir='build')
    opt.load('cppml', tooldir='build')
    opt.load('python')


def configure_cpp_compiler(conf):
    # use clang/clang++ if available
    conf.find_program('clang', var='CC')
    conf.find_program('clang++', var='CXX')
    ccache = conf.find_program('ccache', var='CCACHE', mandatory=False)
    if ccache:
        conf.env['CC'] = ccache + ' ' + conf.env['CC']
        conf.env['CXX'] = ccache + ' ' + conf.env['CXX']

    conf.load('compiler_cxx')
    conf.load('compiler_c')
    conf.load('cxx')
    conf.load('configure_cpp')


def configure_fortran(conf):
    conf.load('compiler_fc')
    conf.env.append_unique('FCFLAGS', ['-ffixed-form', '-fPIC', '-frecursive'])
    conf.check_fortran()
    conf.check_fortran_verbose_flag()
    conf.check_fortran_clib()
    conf.check_fortran_dummy_main()


def configure_python(conf):
    conf.load('python')
    conf.check_python_version((2, 7, 0))
    conf.check_python_headers()

    conf.check_python_module('boto')
    conf.check_python_module('nose')
    conf.check_python_module('numpy')
    conf.check_python_module('requests')

    conf.check_cfg(
        package='python-2.7',
        args='--cflags --libs',
        uselib_store='PYTHON',
        mandatory=True,
        )


def configure_ocaml(conf):
    conf.load('bison')
    conf.load('bison_cppml')
    conf.load('ocaml')


def configure(conf):
    configure_cpp_compiler(conf)

    if ENABLE_FORTRAN:
        configure_fortran(conf)

    configure_python(conf)

    configure_ocaml(conf)
    conf.load('cppml')

    conf.check(lib='blas', mandatory=True)

    conf.check(
        lib="c++" if sys.platform == "darwin" else "stdc++",
        uselib_store='STDC++',
        mandatory=True
        )

    conf.check(lib='crypto', mandatory=True)
    conf.check(lib='lapack', mandatory=True)
    conf.check(lib='rt', mandatory=False)
    conf.check(lib='tcmalloc', mandatory=True)

    conf.check(lib='LLVM-3.5', uselib_store='LLVM', mandatory=True)

    configure_clang(conf)

    configure_boost(conf)

    tcmalloc_flags = [
        '-fno-builtin-malloc', '-fno-builtin-calloc', '-fno-builtin-realloc',
        '-fno-builtin-free'
        ]
    conf.env.CFLAGS_TCMALLOC += tcmalloc_flags
    conf.env.CXXFLAGS_TCMALLOC += tcmalloc_flags

    conf.check_cfg(
        package='libprofiler',
        args='--cflags --libs',
        uselib_store='PROFILER',
        mandatory=False
        )

    conf.check(lib='cuda', uselib_store='CUDA', mandatory=True)
    conf.check(lib='cudart', linkflags=['-L/usr/local/cuda-8.0/lib64'], uselib_store='CUDART', mandatory=True)
    
boost_libs = [
    'boost_date_time',
    'boost_filesystem',
    'boost_python',
    'boost_regex',
    'boost_thread',
    'boost_unit_test_framework'
    ]

def configure_boost(conf):
    for boost_lib in boost_libs:
        use = 'PYTHON' if boost_lib == 'boost_python' else ''
        conf.check(lib=boost_lib, use=use, mandatory=True)

clang_libs = [
    'clangFrontend',
    'clangDriver',
    'clangSerialization',
    'clangCodeGen',
    'clangParse',
    'clangSema',
    'clangAnalysis',
    'clangEdit',
    'clangAST',
    'clangLex',
    'clangBasic',
    ]

def configure_clang(conf):
    for lib in clang_libs:
        conf.check(stlib=lib, mandatory=True)

def getInstallRoot(bld):
    if bld.options.destdir == '':
        return ''
    return os.path.join(bld.options.destdir, bld.env['PYTHONARCHDIR'].replace('/local', ''))

def getInstallPath(bld):
    return os.path.join(getInstallRoot(bld), 'ufora')

def rebuildSubscribableWebObjectsWrapper(bld):
    source_dir = bld.path
    for dirname in ['ufora', 'BackendGateway', 'SubscribableWebObjects']:
        source_dir = source_dir.find_dir(dirname)

    dest_dir = bld.path
    for dirname in ['ufora', 'web', 'relay']:
        dest_dir = dest_dir.find_dir(dirname)

    python_dest_dir = bld.path
    for dirname in ['packages', 'python', 'pyfora']:
        python_dest_dir = python_dest_dir.find_dir(dirname)


    # python ufora/BackendGateway/SubscribableWebObjects/generateCoffeeWrapper.py >
    #        ufora/web/relay/tsunami/coffee/SubscribableWebObjects.coffee
    assert bld.exec_command(
        'PYTHONPATH=`pwd` python %s/generateCoffeeWrapper.py > %s/SubscribableWebObjects.coffee' % (
            source_dir.abspath(),
            dest_dir.abspath()
            )
        ) == 0, "Failed to build python SubscribableWebObjects wrapper"

    # python
    # ufora/BackendGateway/SubscribableWebObjects/generatePythonWrapper.py >
    #       packages/python/pyfora/SubscribableWebObjects.coffee
    assert bld.exec_command(
            'PYTHONPATH=`pwd` python %s/generatePythonWrapper.py > %s/SubscribableWebObjects.py' % (
                source_dir.abspath(),
                python_dest_dir.abspath()
            )
        ) == 0, "Failed to build python SubscribableWebObjects wrapper"



def build(bld):
    """Primary WAF entry point."""
    bld.post_mode = Build.POST_LAZY

    if bld.env.CCACHE:
        bld.nocache = True

    extensions = ('cpp', 'hpp', 'cppml', 'hppml', 'ypp', 'h', 'c', 'cc', 'inc', 'inl', 'gen', 'def')
    folders = ('ufora/', 'third_party/', 'test_scripts/', 'perf_tests')
    excludes = ('ufora/web/',)

    def shouldExclude(x):
        abspath = x.abspath()
        return any(exclude in abspath for exclude in excludes)

    thirdparty_sources = []
    fora_sources = []
    native_sources = []
    test_sources = []
    core_sources = []

    for extension in extensions:
        for folder in folders:
            for source in bld.path.ant_glob("%s**/*.%s" % (folder, extension)):
                if shouldExclude(source):
                    continue

                relpath = source.relpath()

                if relpath.startswith('third_party/'):
                    thirdparty_sources.append(source)
                    continue

                if '.py.' in relpath or relpath.startswith('ufora/native/'):
                    native_sources.append(source)
                    continue

                if relpath.startswith('ufora/core/'):
                    core_sources.append(source)
                    continue

                if 'test.' in relpath:
                    test_sources.append(source)
                    continue

                fora_sources.append(source)


    defaultBuildArgs = {
        "cxxflags": bld.env.CXXFLAGS,
        "defines": bld.env.CXXDEFINES,
        "includes": bld.env.SYS_INCLUDES,
        "libpath": bld.env.LIB_DIRS + [os.path.abspath(out)],
        "linkflags": bld.env.LINKFLAGS,
        "install_path": getInstallPath(bld)
        }

    bld.add_group("PCH")
    includes = list(bld.env['SYS_INCLUDES'])
    for i in bld.env.keys():
        if i.startswith("INCLUDE"):
            includes.extend(bld.env[i])


    bld(
        rule='${CXX} %s %s %s ${SRC} -dD -E -o ${TGT}' % (
            " ".join(bld.env['CXXFLAGS']),
            " ".join(['-D' + x for x in bld.env['CXXDEFINES']]),
            " ".join(['-I' + os.path.abspath(x) for x in includes]),
            ),
        source='ufora/CommonHeaders.hpp',
        target='ufora/CommonHeaders.ii',
        name='make_pch'
        )

    bld.env['CXXFLAGS'] += [
        '-include', os.path.abspath(os.path.join(out, "ufora/CommonHeaders.ii"))
        ]


    bld.add_group("CPPML Prelude")
    cppml_dir = bld.path.find_dir('cppml').abspath()

    bld(
        rule='make -C %s' % cppml_dir,
        source=bld.path.ant_glob('cppml/*.ml'),
        name='make_cppml',
        )

    bld.add_group("Install CPPML")
    bld(
        rule='cp ${SRC} ${TGT}',
        source=bld.path.get_src().find_dir('cppml').find_node('preamble.txt'),
        target=bld.path.get_bld().make_node('tools').make_node('preamble.txt'),
        name='copy_preamble'
        )

    copy_cppml = bld(
        rule='cp ${SRC} ${TGT}',
        source=bld.path.get_src().find_dir('cppml').make_node('cppml'),
        after='make_cppml copy_preamble',
        target=bld.path.get_bld().make_node('tools').make_node('cppml'),
        name='copy_cppml'
        )

    bld.env['CPPML'] = copy_cppml.target.abspath()

    bld.add_group("Build")
    if ENABLE_FORTRAN:
        bld.objects(
            features='fc',
            kind='all',
            source=bld.path.ant_glob('third_party/slsqp_optimiz/*.f*'),
            target='fortran',
            islibrary=True,
            )

    bld.shlib(
        source=thirdparty_sources,
        target='fora_thirdparty',
        features='cxx',
        use=[
            'STDC++',
            ],
        **defaultBuildArgs
        )


    nativeDependencies = [lib.upper() for lib in itertools.chain(clang_libs, boost_libs)] + [
        'BLAS',
        'GFORTRAN',
        'LAPACK',
        'PROFILER',
        'PYTHON',
        'RT',
        'STDC++',
        'TCMALLOC',
        'LLVM',
        'fortran',
        'fora_thirdparty',
        'CUDA',
        'CUDART'
        ]

    bld.shlib(
        source=core_sources,
        target='ufora-core',
        features='cxx',
        use=[lib.upper() for lib in boost_libs] + ['PYTHON', 'fora_thirdparty', 'CRYPTO'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=fora_sources + test_sources,
        target='ufora',
        features='cxx',
        use=nativeDependencies + ['fora_thirdparty', 'ufora-core'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=native_sources,
        target='native',
        features='cxx pyext',
        use=nativeDependencies + ['ufora-core', 'ufora'],
        name='native',
        **defaultBuildArgs
        )


    bld.add_post_fun(post_build)


def post_build(bld):
    rebuildSubscribableWebObjectsWrapper(bld)
    installSourceFiles(bld)


def installSourceFiles(bld):
    if bld.cmd != 'install' or bld.options.destdir == '':
        return
    filesToInstall = bld.path.ant_glob(
        ["ufora/*.py", "ufora/config/**/*.py", "ufora/core/**/*.py", "ufora/cumulus/**/*.py",
         "ufora/distributed/**/*.py", "ufora/FORA/**/*.py", "ufora/kb/**/*.py",
         "ufora/networking/**/*.py",
         "ufora/tsunami/__init__.py", "ufora/tsunami/ComputedValue/**/*.py",
         "ufora/ui/**/*.py", "ufora/util/**/*.py", "ufora/web/__init__.py",
         "ufora/web/BackendGateway/**/*.py", "ufora/FORA/**/*.fora", "fora.py", "fora_eval.py"],
        excl=["**/*test*", "**/*Test*"]
        )
    for fileToInstall in filesToInstall:
        relpath = fileToInstall.path_from(bld.path)
        bld.install_files(
            os.path.join(getInstallRoot(bld), os.path.split(relpath)[0]), fileToInstall
            )
