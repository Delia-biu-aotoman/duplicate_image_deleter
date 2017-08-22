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


class MessageProcess:
    def read_message(self):
        while not self.in_flag.value:
            time.sleep(0.1)
        res = []
        while len(self.in_args) > 0:
            res.append(self.in_args.pop())
        self.in_flag.value = False
        return res

    def send_data(self, messages):
        for m in reversed(messages):
            self.out_args.append(m)
        self.out_flag.value = True
        while self.out_flag.value:
            time.sleep(0.1)

    def send_data_nowait(self, messages):
        for m in reversed(messages):
            self.out_args.append(m)
        self.out_flag.value = True

class AsyncCanvasLoader(MessageProcess):
    def __init__(self):
        self.in_flag = mp.Value(ctypes.c_bool, False)
        self.out_flag = mp.Value(ctypes.c_bool, False)

        input_manager = mp.Manager()
        self.in_args = input_manager.list()

        output_manager = mp.Manager()
        self.out_args = output_manager.list()

        self.idle_flag = mp.Value(ctypes.c_bool, True)

        self.loader = mp.Process(target=self.canvas_loader, args=(
            self.out_args, self.out_flag, self.in_args, self.in_flag, self.idle_flag
        ))

        self.loader.start()

    # Public
    def set_job(self, filename):
        self.idle_flag.value = False
        self.send_data(["job", filename])

    def is_idle(self):
        return self.idle_flag.value

    def get_results(self):
        return self.read_message()

    def quit(self):
        self.send_data(["quit"])
        self.loader.join()

    # Private
    def canvas_loader(self, in_args, in_flag, out_args, out_flag, idle_flag):
        self.is_running = True
        self.filename = None
        self.in_flag = in_flag
        self.in_args = in_args
        self.out_args = out_args
        self.out_flag = out_flag

        while self.is_running:
            if self.in_flag.value:
                self.process_input()

            if self.filename is not None:
                result = self.load_image_data(self.filename)
                self.filename = None
                self.idle_flag.value = True
                self.send_data(["result", result])

    def process_input(self):
        data = self.read_message()
        if len(data) > 0:
            msg_type = data[0]
            if msg_type == "quit":
                self.is_running = False

            elif msg_type == "job":
                if len(data) > 1:
                    self.filename = data[1]
                else:
                    raise ValueError("No paths given to fetch")

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
            "canvas": canvas
        }
        return result

class BackgroundCacher(MessageProcess):
    def __init__(self, in_args, in_flag, out_args, out_flag, max_workers, max_cache_size):
        self.in_args = in_args
        self.in_flag = in_flag
        self.out_args = out_args
        self.out_flag = out_flag
        self.max_workers = max_workers
        self.max_cache_size = max_cache_size

        # Pending cache should have the most important file on the right
        # Since they are cached from right to left.
        self.pending_cache = []
        self.workers = set([])
        worker_count = 0
        self.requested_at = {}
        self.cache = {}

        self.running = True

        while self.running:
            if in_flag.value:
                self.process_input()

            while worker_count < max_workers and len(self.pending_cache) > 0:
                target = self.pending_cache.pop()
                self.workers.add(AsyncCanvasLoader(target))
                worker_count = worker_count + 1

            done_workers = []
            for worker in self.workers:
                if worker.is_done():
                    done_workers.append(worker)

            for worker in done_workers:
                self.workers.remove(worker)
                self.cache[worker.path()] = worker.get_image_list()
                worker_count = worker_count - 1

            while len(self.cache) > self.max_cache_size:
                oldest_time = float("inf")
                oldest_filename = None

                for path, request_time in self.requested_at.items():
                    if path in self.cache and request_time < oldest_time:
                        oldest_time = request_time
                        oldest_filename = path

                if oldest_filename is not None:
                    pass
                    del self.cache[oldest_filename]
                    del self.requested_at[oldest_filename]

            if self.done_caching():
                time.sleep(0.05)

        for worker in self.workers:
            worker.quit()

        del self.pending_cache
        del self.workers
        del self.requested_at
        del self.cache
        #~ time.sleep(2)
        print("Done Cleanup..")

    def done_caching(self):
        return len(self.pending_cache) == 0 and len(self.workers) == 0

    def process_input(self):
        data = self.read_message()
        if len(data) > 0:
            msg_type = data[0]
            if msg_type == "quit":
                self.running = False

            elif msg_type == "fetch":
                if len(data) > 1:
                    filename = data[1]
                    worker = AsyncCanvasLoader(filename)
                    while not worker.is_done():
                        time.sleep(0.1)
                    img_list = worker.get_image_list()
                    self.send_data(img_list)
                else:
                    raise ValueError("No paths given to fetch")

            elif msg_type == "preload":
                self.pending_cache = data[1:]
                for f in self.pending_cache:
                    self.requested_at[f] = time.monotonic()

            elif msg_type == "check_status":
                self.send_data([{
                    "workers_running": len(self.workers),
                    "pending_cache":len(self.pending_cache),
                    "cache_size":len(self.cache)
                }])

# Private Methods
def background_cacher(
    in_args, in_flag, out_args, out_flag, max_workers, max_cache_size):

    """
    Output from this process is input to the other process, and vice versa.
    Therefore, this function swaps the arguments.
    """
    b = BackgroundCacher(
        out_args, out_flag, in_args, in_flag, max_workers, max_cache_size
    )

class ImageCache(MessageProcess):
    def __init__(self, max_workers=16, max_cache_size=32):
        self.in_flag = mp.Value(ctypes.c_bool, False)
        self.out_flag = mp.Value(ctypes.c_bool, False)

        input_manager = mp.Manager()
        self.in_args = input_manager.list()

        output_manager = mp.Manager()
        self.out_args = output_manager.list()

        self.fetcher = mp.Process(target=background_cacher, args=(
            self.in_args, self.in_flag, self.out_args, self.out_flag,
            max_workers, max_cache_size
        ))

        self.fetcher.start()

    def fetch(self, path):
        self.send_data(["fetch", path])
        return self.read_message()

    def preload(self, paths):
        self.send_data(["preload"] + paths)

    def check_status(self):
        self.send_data(["check_status"])
        return self.read_message()

    def quit(self):
        self.send_data(["quit"])
        print("Waiting for join")
        self.fetcher.join()
        print("Join successful")

p = "/home/avery/Downloads/temp/images"
files = os.listdir(p)
paths = [join(p, x) for x in files]


loader = AsyncCanvasLoader()

for i in range(1, 5):
    filename = paths[i]
    loader.set_job(filename)
    while not loader.is_idle():
        pass

    print("Got the result back in main")
    res = loader.get_results()
    pprint(res)

print("Quitting")
loader.quit()

#~ for i in range(0, 100):
    #~ wanted_size = 60
    #~ max_cache_size = 60
    #~ wanted = paths[-wanted_size:]

    #~ print("Total paths:",len(paths))
    #~ print("Cached paths:",len(wanted))

    #~ c = ImageCache(max_workers=16, max_cache_size=max_cache_size)
    #~ c.preload(wanted)

    #~ while True:
        #~ time.sleep(0.01)
        #~ state = c.check_status()[0]
        #~ if state["pending_cache"] == 0 and state["workers_running"] == 0:
            #~ print("All cached")
            #~ break

    #~ c.quit()
