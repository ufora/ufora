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

from setuptools import setup, find_packages
from distutils.core import Extension
import glob
import numpy
import os
import re

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()

def read_package_version():
    version_file = 'pyfora/_version.py'
    with open(version_file, 'rt') as version_file:
        version_line = version_file.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_line, re.M)
    if match:
        return match.group(1)
    raise RuntimeError("Can't read version string from '%s'." % (version_file,))

version = read_package_version()

install_requires = ['futures', 'socketIO-client>=0.6.5', 'numpy', 'wsaccel']

ext_modules = []

extra_compile_args=['-std=c++11']

pythonObjectRehydratorModule = Extension('pyfora.PythonObjectRehydrator',
                                         language='c++',
                                         extra_compile_args=extra_compile_args,
                                         sources=['pyfora/src/pythonObjectRehydratorModule.cpp',
                                                  'pyfora/src/BinaryObjectRegistry.cpp',
                                                  'pyfora/src/StringBuilder.cpp',
                                                  'pyfora/src/PureImplementationMappings.cpp',
                                                  'pyfora/src/PyObjectUtils.cpp',
                                                  'pyfora/src/ObjectRegistry.cpp',
                                                  'pyfora/src/IRToPythonConverter.cpp',
                                                  'pyfora/src/NamedSingletons.cpp',
                                                  'pyfora/src/BinaryObjectRegistryHelpers.cpp',
                                                  'pyfora/src/FreeVariableMemberAccessChain.cpp',
                                                  'pyfora/src/Json.cpp',
                                                  'pyfora/src/PyAbortSingletons.cpp',
                                                  'pyfora/src/ModuleLevelObjectIndex.cpp',
                                                  'pyfora/src/ScopedPyThreads.cpp',
                                                  'pyfora/src/PythonObjectRehydrator.cpp'] +
                                         glob.glob('pyfora/src/TypeDescriptions/*.cpp') +
                                         glob.glob('pyfora/src/serialization/*.cpp'),
                                         include_dirs=[numpy.get_include()]
)

ext_modules.append(pythonObjectRehydratorModule)

stringbuildermodule = Extension('pyfora.StringBuilder',
                                language='c++',
                                extra_compile_args=['-std=c++11'],
                                sources=['pyfora/src/StringBuilder.cpp',
                                         'pyfora/src/stringbuildermodule.cpp']
                                )
ext_modules.append(stringbuildermodule)

binaryObjectRegistryModule = Extension('pyfora.BinaryObjectRegistry',
                                       language='c++',
                                       extra_compile_args=extra_compile_args,
                                       sources=['pyfora/src/BinaryObjectRegistry.cpp',
                                                'pyfora/src/PyObjectWalker.cpp',
                                                'pyfora/src/PureImplementationMappings.cpp',
                                                'pyfora/src/binaryobjectregistrymodule.cpp',
                                                'pyfora/src/StringBuilder.cpp',
                                                'pyfora/src/FileDescription.cpp',
                                                'pyfora/src/PyObjectUtils.cpp',
                                                'pyfora/src/PyAstUtil.cpp',
                                                'pyfora/src/FreeVariableMemberAccessChain.cpp',
                                                'pyfora/src/PyAstFreeVariableAnalyses.cpp',
                                                'pyfora/src/PyforaInspect.cpp',
                                                'pyfora/src/FreeVariableResolver.cpp',
                                                'pyfora/src/Ast.cpp',
                                                'pyfora/src/UnresolvedFreeVariableExceptions.cpp',
                                                'pyfora/src/BinaryObjectRegistryHelpers.cpp',
                                                'pyfora/src/Json.cpp',
                                                'pyfora/src/ModuleLevelObjectIndex.cpp']
                                       )
ext_modules.append(binaryObjectRegistryModule)

pyObjectWalkerModule = Extension('pyfora.PyObjectWalker',
                                 language='c++',
                                 extra_compile_args=extra_compile_args,
                                 sources=['pyfora/src/pyobjectwalkermodule.cpp',
                                          'pyfora/src/PyObjectWalker.cpp',
                                          'pyfora/src/PureImplementationMappings.cpp',
                                          'pyfora/src/BinaryObjectRegistry.cpp',
                                          'pyfora/src/FileDescription.cpp',
                                          'pyfora/src/StringBuilder.cpp',
                                          'pyfora/src/PyObjectUtils.cpp',
                                          'pyfora/src/FreeVariableResolver.cpp',
                                          'pyfora/src/PyAstUtil.cpp',
                                          'pyfora/src/FreeVariableMemberAccessChain.cpp',
                                          'pyfora/src/PyAstFreeVariableAnalyses.cpp',
                                          'pyfora/src/PyforaInspect.cpp',
                                          'pyfora/src/Ast.cpp',
                                          'pyfora/src/UnresolvedFreeVariableExceptions.cpp',
                                          'pyfora/src/BinaryObjectRegistryHelpers.cpp',
                                          'pyfora/src/Json.cpp',
                                          'pyfora/src/ModuleLevelObjectIndex.cpp']
                                 )
ext_modules.append(pyObjectWalkerModule)


setup(
    name='pyfora',
    version=version,
    description="A library for parallel execution of Python code in the Ufora runtime",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering'
    ],
    keywords='ufora fora parallel remote data-science machine-learning',
    author='Ufora Inc.',
    author_email='info@ufora.com',
    url='http://www.ufora.com/',
    license='Apache',
    packages=find_packages('.'),
    package_dir={'': '.'},
    package_data={
        '': ['*.txt', '*.rst'],
        'pyfora': ['fora/**/*.fora']
        },
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['pyfora_aws=pyfora.aws.pyfora_aws:main']
    },
    ext_modules=ext_modules
)

