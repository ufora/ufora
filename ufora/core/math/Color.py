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

import numpy


def hsl_to_rgb(h,s,l):
    q = l * (1.0 + s) * (l < .5) + (l + s - l * s) * (l >= .5)
    p = 2 * l - q
    h = h - numpy.floor(h)
    t = [h + 1.0 / 3.0, h, h - 1.0 / 3.0]
    for ix in range(3):
        t[ix] -= numpy.floor(t[ix])
        t[ix] = ((p + 6 * (q - p) * t[ix]) * (t[ix] < 1.0 / 6.0)
                 + q * (t[ix] >= 1.0 / 6.0) * (t[ix] < 3.0 / 6.0)
                 + (p + 6 * (q - p) * (2.0 / 3.0 - t[ix]) ) * (t[ix] >= 3.0 / 6.0) * (t[ix] < 5.0 / 6.0)
                 + p * (t[ix] >= 5.0 / 6.0))
    return t[0],t[1],t[2]

def hsv_to_rgb(h,s,v):
    f = (h - numpy.floor(h)) * 6.0
    hi = numpy.floor(f)
    f -= hi

    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    hi = hi.astype(int)
    r = v * (hi == 0) + q * (hi == 1) + p * (hi == 2) + p * (hi == 3) + t * (hi == 4) + v * (hi == 5)
    g = t * (hi == 0) + v * (hi == 1) + v * (hi == 2) + q * (hi == 3) + p * (hi == 4) + p * (hi == 5)
    b = p * (hi == 0) + p * (hi == 1) + t * (hi == 2) + v * (hi == 3) + v * (hi == 4) + q * (hi == 5)

    return r,g,b

