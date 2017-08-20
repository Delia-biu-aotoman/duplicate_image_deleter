#!/usr/bin/env python3
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
from stat import *
from similarity import *
from display_results import display

cleanup = True

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
    possible_image_files = []

    all_file_len = 0
    for root, dirs, files in os.walk(folder):
        for f in files:
            all_file_len = all_file_len + 1
            fullpath = join(root, f)
            if os.path.isfile(fullpath):
                possible_image_files.append(fullpath)

    print("all_file_len",all_file_len)
    print("normal file len",len(possible_image_files))
    return possible_image_files

def get_summary(f):
    try:
        return patch_stats(load_image(f), f)
    except OSError as e:
        #~ print("OSError accessing ",f)
        return None
    except TimeoutError as e:
        print("Timeout accessing ",f)
        return None

def cleanup_file(filename):
    if cleanup:
        try:
            os.remove(filename)
        except FileNotFoundError as e:
            pass

@timing
def get_cached_summaries(files):
    return dbmanager.load(files)

@timing
def write_cached_summaries(new_files, summaries, bad_files):
    dbmanager.update(new_files, summaries, bad_files)

@timing
def parallel_get_summaries(new_files, num_threads=16):
    new_summary_arr = []
    if len(new_files) > 0:
        try:
            print("Summarizing new files")
            new_summary_arr = Parallel(n_jobs=num_threads)(delayed(get_summary)(f) for f in new_files)
        except KeyboardInterrupt as e:
            # Allow cancelling easily if something hangs.
            print("Got a keyboard interrupt, quitting")
            raise KeyboardInterrupt("QUIT")
    return new_summary_arr

def get_summaries(files):
    print("Reading summary cache")
    summaries, bad_files = get_cached_summaries(files)

    numfiles = len(files)

    new_files = []
    for f in files:
        if not f in summaries and not f in bad_files:
            new_files.append(f)

    new_summary_arr = parallel_get_summaries(new_files)

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

    if os.system("./fast_match") != 0:
        print("Failed to run fast_match")
        sys.exit(1)

    cleanup_file("summaries.dat")

    scores = []
    with open("matches.dat", "r") as input:
        for line in input:
            score_set = line.split(",")
            distance = float(score_set[0])
            left_num = int(score_set[1])
            right_num = int(score_set[2])
            scores.append([distance, files[left_num], files[right_num]])

    cleanup_file("matches.dat")

    print("\n%d pairs of images are similar and will be displayed" % (len(scores)))
    scores.sort(key=lambda x: x[0])
    return scores

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Usage: Pass the path to a folder as the first argument")
        sys.exit(1)

    if not os.path.exists("fast_match"):
        ret = os.system("make")
        if ret != 0:
            print("Could not compile fast_match, check dependencies")
            sys.exit(1)

    folder = sys.argv[1]
    print("Searching " + folder)

    files = recursive_get_image_files(folder)
    numfiles = len(files)
    print("There are %d files to process" % (numfiles))

    summaries = get_summaries(files)
    files = good_files(files, summaries)
    scores = get_scores(files, summaries)
    display(scores)



