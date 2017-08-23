import multiprocessing as mp
import time
from PIL import Image
from math import ceil
from io import BytesIO
from os.path import join, getsize
import os
import time
import ctypes
from pprint import pprint
import traceback
import sys

# Since processes do not report exceptions to the main process,
# it is necessary to log ALL exceptions.
import logging
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('message_test')
handler = logging.FileHandler('error.log')
handler.setFormatter(formatter)
logger.addHandler(handler)

class AsyncCanvasLoader:
    def __init__(self):
        (self.reader, worker_writer) = mp.Pipe(duplex=False)
        (worker_reader, self.writer) = mp.Pipe(duplex=False)
        self.idle_flag = mp.Value(ctypes.c_bool, True)
        self.result_flag = mp.Value(ctypes.c_bool, False)

        self.loader = mp.Process(target=self.canvas_loader, args=(
            worker_reader, worker_writer, self.idle_flag, self.result_flag
        ))

        self.loader.start()

    # Public Interface
    def set_job(self, filename):
        self.idle_flag.value = False
        self.writer.send({"job":filename})

    def is_idle(self):
        return self.idle_flag.value

    def has_result(self):
        return self.result_flag.value

    def get_result(self):
        self.result_flag.value = False
        self.idle_flag.value = True
        self.writer.send({"fetch":0})
        return self.reader.recv()

    def quit(self):
        self.writer.send({"quit":0})
        self.loader.join()

    # Async and Private
    def canvas_loader(self, reader, writer, idle_flag, result_flag):
        try:
            self.is_running = True
            filename = None
            result = None

            while self.is_running:
                if reader.poll():
                    msg = reader.recv()
                    if "job" in msg:
                        filename = msg["job"]
                    elif "quit" in msg:
                        self.is_running = False
                    elif "fetch" in msg:
                        writer.send(result)
                    else:
                        raise Exception("Unknown command:", msg)

                if filename is not None:
                    result = self.load_image_data(filename)
                    result_flag.value = True
                    filename = None

        except Exception as e:
            logger.error("".join(traceback.format_exception(*sys.exc_info())))

    def load_image_data(self, filename):
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

        result = {
            "width": img_orig.size[0],
            "height": img_orig.size[1],
            "filesize": filesize,
            "canvas": canvas,
            "filename":filename
        }
        return result

class BackgroundCacher:
    def __init__(self, reader, writer, num_workers, max_cache_size):
        self.default_worker = AsyncCanvasLoader()
        workers = []
        for i in range(0, num_workers):
            workers.append(AsyncCanvasLoader())

        self.max_cache_size = max_cache_size
        self.writer = writer
        self.reader = reader

        # Pending cache should have the most important file on the right
        # Since they are cached from right to left.
        self.pending_cache = []
        self.requested_at = {}
        self.cache = {}

        self.running = True
        self.active_workers = 0

        while self.running:
            if reader.poll():
                self.process_input()

            for worker in workers:
                if worker.is_idle() and len(self.pending_cache) > 0:
                    self.active_workers = self.active_workers + 1
                    target = self.pending_cache.pop()
                    worker.set_job(target)

                if worker.has_result():
                    res = worker.get_result()
                    self.cache[res["filename"]] = res
                    self.active_workers = self.active_workers - 1

            while len(self.cache) > self.max_cache_size:
                oldest_time = float("inf")
                oldest_filename = None

                for path, request_time in self.requested_at.items():
                    if path in self.cache and request_time < oldest_time:
                        oldest_time = request_time
                        oldest_filename = path

                if oldest_filename is not None:
                    del self.cache[oldest_filename]
                    del self.requested_at[oldest_filename]

            if self.done_caching():
                time.sleep(0.0001)

        for worker in workers:
            worker.quit()

        self.default_worker.quit()
        print("Done Cleanup..")

    def done_caching(self):
        return len(self.pending_cache) == 0 and self.active_workers == 0

    def process_input(self):
        msg = self.reader.recv()

        if "quit" in msg:
            self.running = False
        elif "fetch" in msg:
            filename = msg["fetch"]
            if not filename in self.cache:
                self.default_worker.set_job(filename)
                while not self.default_worker.has_result():
                    time.sleep(0.0001)

                res = self.default_worker.get_result()
                self.cache[filename] = res
                self.requested_at[filename] = time.monotonic()
                self.writer.send(res)
            else:
                self.writer.send(self.cache[filename])

        elif "preload" in msg:
            self.pending_cache = msg["preload"]
            for f in self.pending_cache:
                self.requested_at[f] = time.monotonic()

        elif "check_status" in msg:
            status_dict = {
                "workers_running": self.active_workers,
                "pending_cache": len(self.pending_cache),
                "cache_size": len(self.cache),
                "cache_remaining": self.max_cache_size - len(self.cache),
                "done_caching": self.done_caching()
            }
            self.writer.send(status_dict)

# Private Methods
def background_cacher(worker_reader, worker_writer, num_workers, max_cache_size):
    try:
        b = BackgroundCacher(
            worker_reader, worker_writer, num_workers, max_cache_size
        )
    except Exception as e:
        logger.error("".join(traceback.format_exception(*sys.exc_info())))

class ImageCache:
    def __init__(self, num_workers, max_cache_size=32):
        (self.reader, worker_writer) = mp.Pipe(duplex=False)
        (worker_reader, self.writer) = mp.Pipe(duplex=False)
        self.worker_writer = worker_writer

        self.fetcher = mp.Process(target=background_cacher, args=(
            worker_reader, worker_writer, num_workers, max_cache_size
        ))

        self.fetcher.start()

    def fetch(self, path):
        self.writer.send({"fetch": path})
        return self.reader.recv()

    def preload(self, paths):
        self.writer.send({"preload": paths})

    def check_status(self):
        self.writer.send({"check_status":0})

        while not self.reader.poll():
            time.sleep(0.0001)

        msg = self.reader.recv()
        return msg

    def quit(self):
        self.writer.send({"quit":0})
        print("Waiting for join")
        self.fetcher.join()
        print("Join successful")


def test_canvas_loader():
    p = "/home/avery/Downloads/temp/images"
    files = os.listdir(p)
    paths = [join(p, x) for x in files]

    loader = AsyncCanvasLoader()

    for i in range(1, 5):
        filename = paths[i]
        loader.set_job(filename)
        while not loader.has_result():
            pass

        print("Got the result back in main")
        res = loader.get_result()
        pprint(res)

    print("Quitting")
    loader.quit()

def test_image_cache():
    p = "/home/avery/Downloads/temp/images"
    files = os.listdir(p)
    paths = [join(p, x) for x in files]

    wanted_size = 20
    max_cache_size = 30
    wanted = paths[:wanted_size]

    print("Total paths:",len(paths))
    print("Cached paths:",len(wanted))

    c = ImageCache(num_workers=4, max_cache_size=max_cache_size)
    c.preload(wanted)

    while True:
        time.sleep(0.1)
        state = c.check_status()
        if state["done_caching"]:
            print("Done caching")
            break

    # Test uncached files
    for i in range(0, 10):
        t0 = time.time()
        res = c.fetch(paths[i])
        #~ pprint(res)
        print("Fetch time cache:",time.time() - t0)

    for i in range(20, 30):
        t0 = time.time()
        res = c.fetch(paths[i])
        #~ pprint(res)
        print("Fetch time uncached:",time.time() - t0)

    c.quit()
    print("All processing complete")

if __name__ == "__main__":
    test_image_cache()
    #~ test_canvas_loader()
