import collections
from threading import Thread, Lock
import multiprocessing as mp
import time
import random
from PIL import Image
from math import ceil
from io import BytesIO
import json
from os.path import join, getsize
import os
import time
import sys
import gi
from pprint import pprint


gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

def load_image_data(filename):
    try:
        img_orig = Image.open(filename)
        filesize = getsize(filename)
    except FileNotFoundError as e:
        print("Expected file %s is missing" % (path))
        print(e)
        return None

    size = (600, 600)
    x_size = size[0]
    y_size = size[1]
    x_resize_ratio = img_orig.size[0] / x_size
    y_resize_ratio = img_orig.size[1] / y_size

    if(x_resize_ratio > y_resize_ratio):
        y_size = ceil(y_size * (y_resize_ratio / x_resize_ratio))
    else:
        x_size = ceil(x_size * (x_resize_ratio / y_resize_ratio))

    img = img_orig.resize((x_size, y_size), Image.ANTIALIAS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(img, ((size[0]-x_size)//2, (size[1]-y_size)//2))

    buff = BytesIO()
    canvas.save(buff, 'ppm')
    contents = buff.getvalue()
    buff.close()
    loader = GdkPixbuf.PixbufLoader.new_with_type('pnm')
    loader.write(contents)
    pixbuf = loader.get_pixbuf()
    loader.close()

    result = {
        "width": img_orig.size[0],
        "height": img_orig.size[1],
        "filesize": filesize,
        "pixbuf": pixbuf
    }
    return result

class AsyncImageLoader:
    def __init__(self, filename):
        self.filename = filename
        self.done = False
        self.result = None
        self.loader = Thread(target=self.process_file, args=(filename,))
        self.loader.start()

    def is_done(self):
        return self.done

    def path(self):
        return self.filename

    def get_image(self):
        self.loader.join()
        return self.result

    def process_file(self, filename):
        self.result = load_image_data(filename)
        self.done = True

class ImageCache:
    # Public Methods
    def __init__(self):
        self.lock = Lock()
        self.cache = {}
        # Most wanted at end for Pop, least wanted at start.
        self.wanted_files = []
        self.requested_at = {}

        self._cache_complete = True
        self.running = True
        self.fetcher = Thread(target=self.background_cacher, args=())
        self.fetcher.start()

    def cache_for_later(self, new_paths):
        self.lock.acquire()
        self._cache_complete = False
        self.wanted_files = new_paths
        for path in new_paths:
            self.requested_at[path] = time.monotonic()

        self.lock.release()

    def cache_complete(self):
        return len(self.wanted_files) == 0 and self._cache_complete

    def load_image(self, path):
        data = None
        self.lock.acquire()
        if not path in self.cache:
            print("Missed cache")
            self.cache[path] = load_image_data(path)
            self.requested_at[path] = time.monotonic()
        else:
            print("Hit cache")
        data = self.cache[path]
        self.lock.release()
        return data

    def quit(self):
        self.lock.acquire()
        self.running = False
        self.lock.release()
        self.fetcher.join()

    # Private Methods
    def missing_files(self):
        return len(self.wanted_files) > 0

    def background_cacher(self):
        """
        Inbound messages:
            cache_for_later >> new_paths: array of string
            load_image >> path
            cache_complete
            quit
        Required Shared Variables:
            message_exists (Set by client)
            message_type
            message_data (Can be string, or nothing)

            result_exists (Set by this)

        """

        workers = set([])
        max_workers = 16
        current_workers = 0
        cache_size = 30

        while self.running:
            self.lock.acquire()
            while current_workers < max_workers and self.missing_files():
                target = self.wanted_files.pop()
                #~ print("Caching:",target)
                self.workers.add(AsyncImageLoader(target))
                current_workers = current_workers + 1

            done_workers = []
            for worker in self.workers:
                if worker.is_done():
                    done_workers.append(worker)

            for worker in done_workers:
                self.workers.remove(worker)
                self.cache[worker.path()] = worker.get_image()
                current_workers = current_workers - 1
                #~ print("Done Caching:",worker.path())

            # Forget oldest files.
            while len(self.cache) > cache_size:
                oldest_time = float("inf")
                oldest_filename = None

                for path, request_time in self.requested_at.items():
                    if path in self.cache and request_time < oldest_time:
                        oldest_time = request_time
                        oldest_filename = path

                if oldest_filename is not None:
                    del self.cache[oldest_filename]
                    del self.requested_at[oldest_filename]

            if len(workers) == 0 and not self.missing_files():
                self._cache_complete = False

            self.lock.release()

            if not self.missing_files():
                time.sleep(0.05)

from os.path import join

p = "/home/avery/Downloads/temp/images/"
import os
files = os.listdir(p)
print("num files = ",len(files))

paths = [join(p, x) for x in files]
c = ImageCache()
wanted = paths[:10]

start_time = time.time()
# Cache all files.
c.cache_for_later(wanted)

while not c.cache_complete():
    time.sleep(0.1)

print("Caching time = ",time.time()-start_time)

c.quit()
print("Done")
