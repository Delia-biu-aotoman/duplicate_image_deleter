import sys
from os import listdir
from os.path import isfile, join
from pprint import pprint
from PIL import Image
import time
from math import ceil

from similarity import load_image, patch_stats, hist_similarity, show
from display_results import display

if(len(sys.argv) < 2):
    print("Pass the name of a folder")
    sys.exit(1)

folder = sys.argv[1]
print("Searching " + folder)

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

#~ @timing
def get_image_files(folder):
    image_files = []
    filecount = len(listdir(folder))
    i = 1
    for f in listdir(folder):
        #~ sys.stdout.write("\rChecking file %d of %d" % (i, filecount))

        if is_image(join(folder, f)):
            image_files.append(f)

        i = i + 1
    #~ print()
    return image_files

@timing
def get_summaries(folder, files):
    summaries = {}
    for i in range(0, len(files)):
        try:
            sys.stdout.write("\rProcessing File %d of %d" % (i+1, len(files)))
            sys.stdout.flush()
            f = files[i]
            summary = patch_stats(load_image(join(folder, f)))
            summaries[f] = summary
        except OSError as e:
            pass
            #~ print()
            #~ print(e)
    print()
    return summaries

def good_files(files, summaries):
    return [f for f in summaries if f in summaries]

#~ @timing
def get_scores(files, summaries):
    numfiles = len(summaries)
    scores = []
    for i in range(0, numfiles):
        for j in range(i+1, numfiles):
            f1 = files[i]
            f2 = files[j]
            score = hist_similarity(summaries[f1], summaries[f2])
            scores.append((score, f1, f2))

    scores.sort(key=lambda x: x[0])
    return scores

files = get_image_files(folder)
numfiles = len(files)
print("There are %d files to process" % (numfiles))
summaries = get_summaries(folder, files)
files = good_files(files, summaries)
scores = get_scores(files, summaries)
display(folder, scores)

