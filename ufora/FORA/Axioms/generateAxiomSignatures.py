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

"""
Run this script to generate a file of axiom signatures which can be fed into Axioms_consistency_test.py.
This generates all axioms, but by default comments them all out. Uncomment the ones you want to test.
"""

import ufora.native
import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as FORANative
import os

dir = os.path.dirname(__file__)
AXIOMS_TO_TEST_FILENAME = os.path.join(dir, "AXIOMS_TO_TEST.txt")

runtime = Runtime.getMainRuntime()
axioms = runtime.getAxioms()

readme_string = '"""\nThis file lists all the axioms we would like to check for consistency in\nAxioms_consistency_test.py. It supports basic python-like commenting\n"""\n\n'

with open(AXIOMS_TO_TEST_FILENAME, "w") as f:
    f.write(readme_string)
    f.write('"""\n')
    for i in range(axioms.axiomCount):
        f.write("%s\n" %axioms.getAxiomGroupByIndex(i).signature())
    f.write('"""')

