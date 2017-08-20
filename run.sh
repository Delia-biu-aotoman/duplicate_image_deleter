#!/bin/bash
set -eu
clang++ -Wshadow -Wall -msse2 -msse3 -msse4 -mavx2 -std=c++11 -pthread find_matches.cpp -o fast_match
/usr/bin/time -v ./fast_match
