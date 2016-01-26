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


import pyfora.PureImplementationMapping as PureImplementationMapping


class BetaFunction:
    def __call__(self, a, b):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        
        return __inline_fora(
            """fun(PyFloat(...) a, PyFloat(...) b) { 
                   return PyFloat(`beta(a.@m, b.@m))
                   }"""
            )(a, b)


class GammaFunction:
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(x) {
                   return PyFloat(`tgamma(x.@m))
                   }"""
            )(x)


class Hyp2f1:
    def __call__(self, a, b, c, z):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        if not isinstance(c, float):
            c = float(c)
        if not isinstance(z, float):
            z = float(z)
        
        return __inline_fora(
            """fun(a, b, c, z) {
                   return PyFloat(`hyp2f1(a.@m, b.@m, c.@m, z.@m))
                   }"""
            )(a, b, c, z)


def generateMappings():
    tr = []
    try:
        import scipy.special
        tr.append(
            PureImplementationMapping.InstanceMapping(
                scipy.special.beta,
                BetaFunction
                )
            )
        tr.append(
            PureImplementationMapping.InstanceMapping(
                scipy.special.gamma,
                GammaFunction
                )
            )
        tr.append(
            PureImplementationMapping.InstanceMapping(
                scipy.special.hyp2f1,
                Hyp2f1
                )
            )
    except ImportError:
        pass

    return tr
    
    
