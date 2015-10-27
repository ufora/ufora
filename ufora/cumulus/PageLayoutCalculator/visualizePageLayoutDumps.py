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

import current_contents as mc_cur
import added_contents as mc_add
import long_term_contents as mc_lt
import matplotlib.pyplot as plt


class AxesSequence(object):
    """Creates a series of axes in a figure where only one is displayed at any
    given time. Which plot is displayed is controlled by the arrow keys."""
    def __init__(self):
        self.fig = plt.figure()
        self.axes = []
        self._i = 0 # Currently displayed axes index
        self._n = 0 # Last created axes index
        self.fig.canvas.mpl_connect('key_press_event', self.on_keypress)

    def new(self):
        # The label needs to be specified so that a new axes will be created
        # instead of "add_axes" just returning the original one.
        ax = self.fig.add_axes([0.1, 0.1, 0.35, 0.8], 
                               visible=False, label=self._n)
        self._n += 1
        self.axes.append(ax)
        
        ax2 = self.fig.add_axes([0.55, 0.1, 0.35, 0.8], 
                               visible=False, label=self._n)
        self._n += 1
        self.axes.append(ax2)
        return ax,ax2

    def on_keypress(self, event):
        if event.key == 'right':
            self.next_plot()
        elif event.key == 'pagedown':
            self.next_plot(20)
        elif event.key == 'left':
            self.next_plot(-1)
        elif event.key == 'pageup':
            self.next_plot(-20)
        else:
            return
        self.fig.canvas.draw()

    def next_plot(self, ct = 1):
        self.axes[self._i].set_visible(False)
        self.axes[self._i+1].set_visible(False)

        self._i = max(0, min(len(self.axes)-2, self._i + 2 * ct))

        self.axes[self._i].set_visible(True)
        self.axes[self._i+1].set_visible(True)

        

            

    def show(self):
        self.axes[0].set_visible(True)
        self.axes[1].set_visible(True)
        plt.show()

axes = AxesSequence()

ix = 0
for frameIx in range(len(mc_cur.frames)):
    ix += 1
    p1,p2 = axes.new()

    for f in mc_add.frames[frameIx]:
        if f['y']:
            p1.scatter(f['y'],f['x'],s=[x*2 for x in f['s']],c=f['c'],linewidths=f['linewidths'],alpha=.5)
            p1.set_xlim(-0.05,1.05)
            p1.set_ylim(0,80)
            p1.set_title("Added in Frame %s" % ix)

    for f in mc_lt.frames[frameIx]:
        if f['y']:
            p2.scatter(f['y'],f['x'],s=[x*2 for x in f['s']],c=f['c'],linewidths=f['linewidths'],alpha=.5)
            p2.set_xlim(-0.05,1.05)
            p2.set_ylim(0,80)
            p2.set_title("Longterm in Frame %s" % ix)
    
axes.show()
