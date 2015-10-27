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

import math
import time

class ExponentialMovingAverage:
    """A class to help track time-rates of things (like download rates).

    We model the exponential moving average of f(t) where 'f' consists of a sequence of rectangles.

    You can add additional rectangles with increasing timestamps, and each time we'll discount
    the existing rectangles and add the new one.

    Note that the EMA of a rectangle of height h and width w (under decay d) is 

        h * (1.0 - e^(-w/d))

    so the first time you stick a rectangle in, you'll get less than the average you added. If
    you repeatedly add rectangles of the same height and width (spaced with that width), as

        ema.observe(avg, width, 0.0)
        ema.observe(avg, width, 0.0 + width)
        ema.observe(avg, width, 0.0 + width * 2)
        ema.observe(avg, width, 0.0 + width * 3)
        ema.observe(avg, width, 0.0 + width * 4)

    etc. you'll end up asymptotically approaching 'avg' as the overall moving average.
    """
    def __init__(self, decay):
        self.cur = 0.0
        self.lastTime = 0.0
        self.decay = decay

    def observe(self, avg, width, obsTime = None):
        if obsTime is None:
            obsTime = time.time()

        elapsed = obsTime - self.lastTime
        self.cur *= math.exp(-elapsed / self.decay)
        self.cur += avg * (1.0 - math.exp(-width / self.decay))
        self.lastTime = obsTime

    def currentRate(self):
        return self.cur


