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
import dbmanager

from similarity import *
from display_results import display

cleanup = False

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

@timing
def get_cached_summaries(files):
    return dbmanager.load(files)

@timing
def write_cached_summaries(new_files, summaries, bad_files):
    dbmanager.update(new_files, summaries, bad_files)

@timing
def parallel_get_summaries(files, num_threads=16):
    print("Reading summary cache")
    summaries, bad_files = get_cached_summaries(files)

    numfiles = len(files)

    new_files = []
    for f in files:
        if not f in summaries and not f in bad_files:
            new_files.append(f)

    new_summary_arr = []
    if len(new_files) > 0:
        print("Summarizing new files")
        new_summary_arr = Parallel(n_jobs=num_threads)(delayed(file_to_summary)(f) for f in new_files)

    summarized_files = []
    for i in range(0, len(new_summary_arr)):
        summary = new_summary_arr[i]
        filename = new_files[i]
        if summary is None:
            bad_files.add(filename)
        else:
            summarized_files.append(filename)
            summaries[filename] = summary

    print("Updating summary cache")
    write_cached_summaries(summarized_files, summaries, bad_files)
    return summaries

def good_files(files, summaries):
    return [f for f in files if f in summaries]

@timing
def get_scores(files, summaries):
    # clean up files if they exist

    # Transform the summaries dict into an array for C++ ease
    with open("summaries.dat", "w") as output:
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

    os.system("./fast_match");

    if(cleanup):
        try:
            os.remove("summaries.dat")
        except:
            pass

    scores = []
    with open("matches.dat", "r") as input:
        for line in input:
            score_set = line.split(",")
            distance = float(score_set[0])
            left_num = int(score_set[1])
            right_num = int(score_set[2])
            scores.append([distance, files[left_num], files[right_num]])

    if(cleanup):
        try:
            os.remove("matches.dat")
        except:
            pass

    print("\n%d pairs of images are similar and will be displayed" % (len(scores)))
    scores.sort(key=lambda x: x[0])
    return scores

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Pass the name of a folder")
        sys.exit(1)

    folder = sys.argv[1]
    print("Searching " + folder)

    files = recursive_get_image_files(folder)
    numfiles = len(files)
    print("There are %d files to process" % (numfiles))

    summaries = parallel_get_summaries(files)
    files = good_files(files, summaries)

    scores = get_scores(files, summaries)

    display(scores)



