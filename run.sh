#!/bin/bash
clang++ -Wshadow -Wall -msse2 -msse3 -msse4 -mavx2 -std=c++11 -pthread find_matches.cpp && time ./a.out
