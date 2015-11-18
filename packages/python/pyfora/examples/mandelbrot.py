import time
import pyfora

connection = pyfora.connect("http://localhost:30000")

def escapeTime(c, maxIter=2048):
    z = c
    for ix in xrange(maxIter):
        z = z * z + c
        if (z * z.conjugate()).real > 4.0:
            return ix
    return ix

def linspace(low, high, count):
    count = int(count)
    step = float(high-low)/(count-1)
    return [low + step * ix for ix in xrange(count)]

def f(xres, yres ,xstart=-2.0,xstop=.5,ystart=-1.0,ystop=1.0):
    xs = linspace(xstart, xstop, xres)
    ys = linspace(ystart, ystop, yres)
    
    return [[escapeTime(complex(x,y)) for x in xs] for y in ys]


import numpy as np
import matplotlib.pyplot as plt
import Queue

Z = connection.submit(f,10,10).result().toLocal().result()

import threading

# A class that will downsample the data and recompute when zoomed.
class DataDisplayDownsampler(object):
    def __init__(self, fig, im):
        self.im = im
        self.fig = fig
        self.q = Queue.Queue()
        self.drawQueue = Queue.Queue()
        self.thread = threading.Thread(target=self.updateLoop)
        self.thread.daemon=True
        self.thread.start()

    def update(self, ax):
        # Update the line
        lims = ax.viewLim
        xstart, xend = lims.intervalx
        ystart, yend = lims.intervaly

        dims = ax.axesPatch.get_window_extent().bounds
        width = int(dims[2] + 0.5) * 2
        height = int(dims[3] + 0.5) * 2

        self.q.put((width, height, xstart, xend, yend, ystart))

    def updateLoop(self):
        while True:
            params = self.q.get()

            try:
                while True:
                    params = self.q.get_nowait()
            except Queue.Empty:
                pass

            width, height, xstart, xend, yend, ystart = params

            scaleOut = 32

            while self.q.empty() and scaleOut > 1:
                result = connection.submit(f, width / scaleOut, height / scaleOut, xstart, xend, yend, ystart)
                success = False

                while not success and self.q.empty():
                    try:
                        data = result.result(timeout=.1)
                        success = True
                    except:
                        pass

                if success:
                    scaleOut /= 2

                    data = data.toLocal().result()

                    self.drawQueue.put((data,params))
                else:
                    result.cancel()

    def drawBackground(self):
        res = None
        try:
            while True:
                res = self.drawQueue.get_nowait()
        except Queue.Empty:
            pass

        if res is not None:
            data, (width, height, xstart, xend, yend, ystart) = res

            self.im.set_extent((xstart,xend,ystart,yend))
            self.im.set_data(data)
            ax.figure.canvas.draw_idle()

fig, ax = plt.subplots()

# Hook up the line
im = ax.imshow(Z, cmap=plt.cm.prism, interpolation='none', extent=(-2, .5, -1, 1))
#ax.xlabel("Re(c)")
#ax.ylabel("Im(c)")

d = DataDisplayDownsampler(fig, im)

timer = fig.canvas.new_timer(interval=100)
timer.add_callback(d.drawBackground)
timer.start()

ax.set_autoscale_on(False)

# Connect for changing the view limits
ax.callbacks.connect('xlim_changed', d.update)

plt.show()
