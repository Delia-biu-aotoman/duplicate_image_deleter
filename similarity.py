from scipy import misc
from PIL import Image
import numpy as np
import math
from math import floor
import signal
import errno
from functools import wraps
import os

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator

@timeout(10)
def load_image(filename):
    # Load with alpha channel to prevent possible error on transparent images.
    im = misc.imread(filename, flatten=False, mode='RGBA')
    return im

def hist_similarity(h1, h2):
    return np.linalg.norm(h1 - h2)

x_buckets = 8
y_buckets = 8

def get_summary_size():
    return x_buckets*y_buckets*3

def patch_stats(im, filename):
    if(len(im.shape) != 3):
        return None

    x_high = im.shape[0]
    y_high = im.shape[1]

    if(x_high < x_buckets or y_high < y_buckets):
        # Tiny images not supported.
        return None

    x_pixels = np.array(range(0, x_high))
    y_pixels = np.array(range(0, y_high))

    # This is the easiest way to get ranges which are guaranteed to have
    # roughly equal sizes, even for small images.
    x_ranges = np.array_split(x_pixels, x_buckets)
    y_ranges = np.array_split(y_pixels, y_buckets)

    cmeans = []

    for x in x_ranges:
        x0 = x[0]
        x1 = x[-1]+1

        for y in y_ranges:
            y0 = y[0]
            y1 = y[-1]+1

            patch_pixels = (x1 - x0) * (y1 - y0)
            scale = 1/patch_pixels

            patch = im[x0:x1, y0:y1]

            r_mean = np.mean(patch[:,:,0])
            g_mean = np.mean(patch[:,:,1])
            b_mean = np.mean(patch[:,:,2])
            # Ignoring alpha channel.

            cmeans = cmeans + [r_mean, g_mean, b_mean]

    arr_of_hist = np.array(cmeans).flatten()
    return arr_of_hist

