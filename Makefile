fast_match: fast_match.cpp
	$(CXX) -Wshadow -Wall -msse2 -msse3 -msse4 -mavx2 -std=c++11 -pthread fast_match.cpp -o fast_match
