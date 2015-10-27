#!/usr/bin/env python2
# encoding: utf-8

import copy
import os
from waflib import Build, Utils, TaskGen
import sys

ENABLE_FORTRAN = (sys.platform != "darwin")

APPNAME = 'fora'
VERSION = '0.0.1a'

MODULE_NAME = 'native'

top = '.'
out = '.build' if 'WAF_OUT' not in os.environ else os.environ['WAF_OUT']

import waflib.Tools.c_preproc as c_preproc
c_preproc.strict_quotes = True

def options(opt):
    opt.load('compiler_cxx')
    opt.load('compiler_c')
    opt.load('cxx')
    opt.load('compiler_fc')
    opt.load('configure_cpp')
    opt.load('gcov')
    opt.load('bison_cppml')
    opt.load('ocaml')
    opt.load('cppml')
    opt.load('python')
    opt.add_option(
        '--skip-runtime-dependencies',
            action='store_true',
            default=False,
            dest='skip_runtime_dependencies',
            help='Skip checks for dependencies that are not needed to build.')


def configure(conf):
    # use clang/clang++ if available
    conf.find_program('clang', var='CC')
    conf.find_program('clang++', var='CXX')

    conf.load('compiler_cxx')
    conf.load('compiler_c')
    conf.load('cxx')

    if ENABLE_FORTRAN:
        conf.load('compiler_fc')
        conf.env.append_unique('FCFLAGS', ['-ffixed-form', '-fPIC', '-frecursive'])
        conf.check_fortran()
        conf.check_fortran_verbose_flag()
        conf.check_fortran_clib()
        conf.check_fortran_dummy_main()

    conf.load('configure_cpp')

    conf.load('python')
    conf.check_python_version((2, 7, 0))
    conf.check_python_headers()

    conf.check_python_module('argparse')
    conf.check_python_module('boto')
    conf.check_python_module('coverage', mandatory=False)
    conf.check_python_module('markdown')
    conf.check_python_module('nose')
    conf.check_python_module('numpy')
    conf.check_python_module('os')
    conf.check_python_module('paramiko')
    conf.check_python_module('re')
    conf.check_python_module('redis')
    conf.check_python_module('requests')
    conf.check_python_module('sys')
    conf.check_python_module('unittest')
    conf.check_python_module('xml')
    conf.check_python_module('zlib')

    conf.load('gcov')
    conf.load('bison')
    conf.load('bison_cppml')
    conf.load('ocaml')
    conf.load('cppml')

    if conf.env['CXX'][0].find("pgcc") == -1:
        #use distCC only if we're not using pgcc
        conf.load('distcc')

    conf.check_cfg(
        package='python-2.7',
        args='--cflags --libs',
        uselib_store='PYTHON',
        mandatory=True,
        )

    conf.check(
        lib='blas',
        uselib_store='BLAS',
        mandatory=True,
        )

    cpplib = "c++" if sys.platform == "darwin" else "stdc++"
    conf.check(
        lib=cpplib,
        uselib_store='STDC++',
        mandatory=True,
        )

    conf.check(
        lib='crypto',
        uselib_store='CRYPTO',
        mandatory=True,
        )

    conf.check(
        lib='lapack',
        uselib_store='LAPACK',
        mandatory=True,
        )

    conf.check(
        lib='rt',
        uselib_store='RT',
        mandatory=False,
        )

    conf.check(
        lib='tcmalloc',
        uselib_store='TCMALLOC',
        mandatory=True,
        )

    conf.check(
        lib='LLVM-3.5',
        uselib_store='LLVM',
        mandatory=True,
        )

    configure_clang(conf)

    conf.env.CFLAGS_TCMALLOC += [
        '-fno-builtin-malloc', '-fno-builtin-calloc', '-fno-builtin-realloc',
        '-fno-builtin-free'
        ]
    conf.env.CXXFLAGS_TCMALLOC += [
        '-fno-builtin-malloc', '-fno-builtin-calloc', '-fno-builtin-realloc',
        '-fno-builtin-free'
        ]

    conf.check_cfg(
        package='libprofiler',
        args='--cflags --libs',
        uselib_store='PROFILER',
        mandatory=False,
        )

    if not conf.options.skip_runtime_dependencies:
        # coretools
        conf.find_program("find", var="FIND")
        conf.find_program("killall", var="KILLALL")
        conf.find_program("tar", var="TAR")
        conf.find_program("xz", var="XZ")

        # needed to run
        conf.find_program("coffee", var="COFFEE")
        conf.find_program("node", var="NODE")

        # needed to test
        conf.find_program("mocha", var="MOCHA")
        conf.find_program("redis-cli", var="REDIS_CLI")

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
        conf.check(
            stlib=lib,
            mandatory=True,
            )

def addArg(args, **kwargs):
    tr = dict(args)
    tr.update(kwargs)
    return tr

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

    if bld.env['CXX'][0].find("pgcc") == -1:
        bld.load('distcc')

    extensions = ('cpp', 'hpp', 'cppml', 'hppml', 'ypp', 'h', 'c', 'cc', 'inc', 'inl', 'gen', 'def')
    folders = ('ufora/', 'third_party/', 'test_scripts/', 'perf_tests')
    excludes = ('opengl/MesaOffscreen', 'ufora/web/', 'third_party/boost_1_53_0/boost')
    boost_libs_root = 'third_party/boost_1_53_0/libs'

    def shouldExclude(x):
        abspath = x.abspath()
        for exclude in excludes:
            if exclude in abspath:
                return True

        return False

    def getLibNameForBoostSourceFile(x):
        splitPath = os.path.relpath(x, boost_libs_root).split(os.path.sep)
        libname = splitPath[0]
        subdir = splitPath[1]
        if libname in boost_sources and \
                subdir == 'src' and \
                splitPath[-1] != 'cpp_main.cpp' and \
                splitPath[-1] != 'test_main.cpp' and \
                x.find('win32') == -1:
            return libname
        return None

    thirdparty_sources = []
    fora_sources = []
    native_sources = []
    test_sources = []
    boost_sources = {
            'date_time': [],
            'filesystem': [],
            'python': [],
            'regex': [],
            'system': [],
            'thread': [],
            'test': []
            }

    for extension in extensions:
        for folder in folders:
            for source in bld.path.ant_glob("%s**/*.%s" % (folder, extension)):
                if shouldExclude(source):
                    continue

                relpath = source.relpath()

                if relpath.startswith(boost_libs_root):
                    libname = getLibNameForBoostSourceFile(relpath)
                    if libname is not None:
                        boost_sources[libname].append(source)
                    continue

                if relpath.startswith('third_party/'):
                    thirdparty_sources.append(source)
                    continue

                if 'test.' in relpath:
                    test_sources.append(source)
                    continue

                if relpath.startswith('ufora/native/tests'):
                    test_sources.append(source)
                    continue

                if '.py.' in relpath:
                    native_sources.append(source)
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
        source=boost_sources['date_time'],
        target='fora_boost_date_time',
        features='cxx',
        use=['STDC++'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=boost_sources['filesystem'],
        target='fora_boost_filesystem',
        features='cxx',
        use=['STDC++', 'fora_boost_system'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=boost_sources['python'],
        target='fora_boost_python',
        features='cxx',
        use=['STDC++', 'PYTHON'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=boost_sources['system'],
        target='fora_boost_system',
        features='cxx',
        use=['STDC++'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=boost_sources['regex'],
        target='fora_boost_regex',
        features='cxx',
        use=['STDC++', 'fora_boost_system'],
        **defaultBuildArgs
        )

    bld.shlib(
        source=boost_sources['thread'],
        target='fora_boost_thread',
        features='cxx',
        use=['STDC++', 'fora_boost_system'],
        **defaultBuildArgs
        )

    boost_test_buidArgs = copy.deepcopy(defaultBuildArgs)
    boost_test_buidArgs['defines'].append('BOOST_TEST_DYN_LINK=1')
    bld.shlib(
        source=boost_sources['test'],
        target='fora_boost_unit_test_framework',
        features='cxx',
        use=['STDC++'],
        **boost_test_buidArgs
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

    if sys.platform == "darwin":
        # Exclude fortran, tcmalloc, gfortran until suitable libraries can be found that link
        # properly. william 2013-07-07
        nativeDependencies = [
            'BLAS',
            'CRYPTO',
            'LAPACK',
            'PROFILER',
            'PYTHON',
            'RT',
            'STDC++',

            'fora_boost_date_time',
            'fora_boost_filesystem',
            'fora_boost_python',
            'fora_boost_regex',
            'fora_boost_system',
            'fora_boost_thread',
            'fora_boost_unit_test_framework',
            'fora_thirdparty',
            ]
    else:
        nativeDependencies = [lib.upper() for lib in clang_libs] + [
            'BLAS',
            'CRYPTO',
            'GFORTRAN',
            'LAPACK',
            'PROFILER',
            'PYTHON',
            'RT',
            'STDC++',
            'TCMALLOC',
            'LLVM',
            'fortran',

            'fora_boost_date_time',
            'fora_boost_filesystem',
            'fora_boost_python',
            'fora_boost_regex',
            'fora_boost_system',
            'fora_boost_thread',
            'fora_boost_unit_test_framework',
            'fora_thirdparty',
            ]

    bld.shlib(
        source=fora_sources + native_sources + test_sources,
        target='native',
        features='cxx pyext',
        use=nativeDependencies,
        name='native',
        **defaultBuildArgs
        )

    bld.add_post_fun(rebuildSubscribableWebObjectsWrapper)

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

def analyze(ctx):
    ctx.load('gcov')

