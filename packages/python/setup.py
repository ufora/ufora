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
    }
)

