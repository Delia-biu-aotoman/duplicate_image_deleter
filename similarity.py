from scipy import misc
from PIL import Image
import numpy as np
import math
from math import floor

def load_image(filename):
    im = misc.imread(filename)
    return im

def hist_similarity(h1, h2):
    return np.linalg.norm(h1.flatten() - h2.flatten())

def patch_stats(im):
    x_buckets = 10
    y_buckets = 10

    x_step = floor(im.shape[0]/x_buckets)
    y_step = floor(im.shape[1]/y_buckets)

    cmeans = []

    x0 = 0
    x1 = x_step
    y0 = 0
    y1 = y_step
    while(x1 <= im.shape[0]):
        if (im.shape[0] < x1 + x_step):
            x1 = im.shape[0]

        y0 = 0
        y1 = y_step
        y0 = 0
        y1 = y_step
        while(y1 <= im.shape[1]):
            if (im.shape[1] < y1 + y_step):
                y1 = im.shape[1]

            patch_pixels = (x1 - x0) * (y1 - y0)
            scale = 1/patch_pixels

            patch = im[x0:x1, y0:y1]
            r_mean = np.mean(patch[:,:,0])
            g_mean = np.mean(patch[:,:,1])
            b_mean = np.mean(patch[:,:,2])

            cmeans = cmeans + [r_mean, g_mean, b_mean]
            y0 = y1
            y1 = y1 + y_step

        x0 = x1
        x1 = x1 + x_step

    arr_of_hist = np.array(cmeans).flatten()
    return arr_of_hist

def closeness(path1, path2):
    im1 = load_image(path1)
    im2 = load_image(path2)
    h1 = patch_stats(im1)
    h2 = patch_stats(im2)
    return hist_similarity(h1, h2)

def grayscale(im):
    return np.mean(im[:,:,0:3],2)

def show(image):
    Image.fromarray(image).show()

