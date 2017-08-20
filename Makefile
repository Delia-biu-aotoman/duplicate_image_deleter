fast_match: fast_match.cpp
	$(CXX) -o3 -Wshadow -Wall -mavx -std=c++11 -pthread fast_match.cpp -o fast_match
