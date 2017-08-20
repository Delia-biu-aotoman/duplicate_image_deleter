import sys
from os import listdir
import os
from os.path import isfile, join
from pprint import pprint
from PIL import Image
import time
from math import ceil
import json
import numpy as np
from joblib import Parallel, delayed
import multiprocessing

from similarity import *
from display_results import display

def is_image(path):
    # Perform mimetype check for speed?
    return True


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print ('%s function took %0.3f ms' % (f.__name__, (time2-time1)*1000.0))
        return ret
    return wrap

@timing
def recursive_get_image_files(folder):
    image_files = []

    for root, dirs, files in os.walk(folder):
        for f in files:
            fullpath = join(root, f)
            image_files.append(fullpath)

    return image_files

def file_to_summary(f):
    try:
        return patch_stats(load_image(f), f)
    except OSError as e:
        return None

def get_score_line(files, summaries, i):
    max_score = 300
    numfiles = len(files)
    scores = []

    for j in range(i+1, numfiles):
        f1 = files[i]
        f2 = files[j]
        score = np.linalg.norm(summaries[f1] - summaries[f2])
        if score < max_score:
            scores.append((score, f1, f2))

    return scores

@timing
def get_scores(files, summaries, num_threads=4):
    numfiles = len(files)
    scores = []

    all_scores = Parallel(n_jobs=num_threads)(delayed(get_score_line)(files, summaries, i) for i in range(0, numfiles))
    for score_set in all_scores:
        scores = scores + score_set
    del(all_scores)

    print("\n%d pairs of images are similar and will be displayed" % (len(scores)))
    scores.sort(key=lambda x: x[0])
    return scores

@timing
def parallel_get_summaries(files, summaries, num_threads=16):
    numfiles = len(files)

    summary_arr = Parallel(n_jobs=num_threads)(delayed(file_to_summary)(f) for f in files)

    for i in range(0, numfiles):
        summary = summary_arr[i]
        if summary is not None:
            filename = files[i]
            summaries[filename] = summary

def good_files(files, summaries):
    return [f for f in files if f in summaries]

def get_cache():
    try:
        processed = {}
        with open("cache.json", "r") as input:
            numpy_summaries = {}
            unprocessed = json.loads(input.read())
            if "summaries" in unprocessed:
                for filename, summary in unprocessed["summaries"].items():
                    #~ numpy_summaries[filename] = np.array(summary, dtype="uint8")
                    numpy_summaries[filename] = np.array(summary)

                processed["summaries"] = numpy_summaries
            else:
                processed["summaries"] = {}
        return processed
    except FileNotFoundError as e:
        return {"summaries":{}}

def write_cache(data):
    generic_summaries = {}
    for filename, summary in data["summaries"].items():
        generic_summaries[filename] = summary.tolist()

    processed = {"summaries": generic_summaries}

    with open("cache.json", "w") as output:
        output.write(json.dumps(processed))

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Pass the name of a folder")
        sys.exit(1)

    data = get_cache();

    folder = sys.argv[1]
    print("Searching " + folder)

    files = recursive_get_image_files(folder)
    numfiles = len(files)
    print("There are %d files to process" % (numfiles))

    summaries = data["summaries"]
    #~ parallel_get_summaries(files, summaries)
    files = good_files(files, summaries)
    # Turn this part alone into C

    # Transform the summaries dict into an array for C++ ease
    with open("temp.dat", "w") as output:
        # Write number of entries
        output.write(str(len(files)) + "\n")

        # Write length of each summary
        summary_len = get_summary_size()
        output.write(str(summary_len) + "\n")
        for f in files:
            # Each summary is an 8*8*3 array of floats
            summary = summaries[f].tolist()
            summary_strings = [str(s) for s in summary]
            summary_s = ",".join(summary_strings)
            output.write(summary_s + "\n")

    #~ scores = get_scores(files, summaries)

    #~ display(scores)



