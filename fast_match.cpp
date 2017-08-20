#include <fstream>
#include <iostream>
#include <cstdlib>
#include <cmath>
#include <thread>
#include <vector>
#include <string>
#include <math.h>
#include <immintrin.h>

#define NUM_THREADS 8
#define ARR_SIZE 192
#define val(filenum,i) (data[ARR_SIZE*filenum + i])

struct match
{
    int left;
    int right;
    float distance;
};

inline float norm(const float* x, const float* y)
{
    float sum_of_squares;
    //Add the vectors 8 at a time. Don't need to check for remainder.
    __m256 eight_sums = _mm256_setzero_ps();
    for (int n = ARR_SIZE; n>=8; n-=8){
        const __m256 a = _mm256_loadu_ps(x);
        const __m256 b = _mm256_loadu_ps(y);
        const __m256 a_minus_b = _mm256_sub_ps(a,b);
        const __m256 a_minus_b_squared = _mm256_mul_ps(a_minus_b, a_minus_b);
        eight_sums = _mm256_add_ps(eight_sums, a_minus_b_squared);
        x+=8;
        y+=8;
    }

    //Convert 8sum into a 4sum
    __m128 four_left_regs = _mm256_extractf128_ps(eight_sums, 0);
    __m128 four_right_regs = _mm256_extractf128_ps(eight_sums, 1);
    __m128 four_sums = _mm_add_ps(four_left_regs, four_right_regs);
    //Convert 4sum into a 1sum
    __m128 two_sums_padded = _mm_hadd_ps(four_sums, four_sums);
    __m128 one_sum_padded = _mm_hadd_ps(two_sums_padded, two_sums_padded);
    sum_of_squares = _mm_cvtss_f32(one_sum_padded);
    return sqrt(sum_of_squares);
}

void do_work(std::vector<match>* matches, const float* data, int thread_num, int num_files, int arr_size){
    const float max_dist = 300;
    float dist;
    for(int i = thread_num; i < num_files; i = i + NUM_THREADS){
        for(int j = i + 1; j < num_files; ++j){
             dist = norm(data+i*ARR_SIZE, data+j*ARR_SIZE);
             if (dist < max_dist){
                 matches->push_back(match());
                 matches->back().left = i;
                 matches->back().right = j;
                 matches->back().distance = dist;
             }
        }
    }
}

void search(const float* data, int num_files, int arr_size)
{
    std::vector<match>* results[NUM_THREADS];
    std::thread pool[NUM_THREADS];

    for(int t = 0; t < NUM_THREADS; ++t){
        results[t] = new std::vector<match>();
        //~ pool[t] = std::thread(do_work, t, data, num_files, arr_size);
        pool[t] = std::thread(do_work, results[t], data, t, num_files, arr_size);
    }

    std::cout <<"Waiting for threads" << std::endl;
    for(auto& t: pool){
        t.join();
    }

    std::ofstream output("matches.dat");

    for(int t = 0; t < NUM_THREADS; ++t){
        std::cout << "number of results in thread " << t << " = " << results[t]->size() << std::endl;
        for(auto const& m: *results[t]){
            output << m.distance << "," << m.left << "," << m.right << std::endl;
        }
        delete(results[t]);
    }
    output.close();
}

int main()
{
    const char* filename = "summaries.dat";

    int arr_size, num_files;
    std::ifstream infile(filename);
    infile >> num_files;
    infile >> arr_size;

    if(arr_size != ARR_SIZE){
        std::cout <<"Invalid file" << std::endl;
        std::exit(EXIT_FAILURE);
    }

    float* data = new float[num_files * arr_size * sizeof(float)];
    char delim;

    for(int f = 0; f < num_files; ++f){
        for(int i = 0; i < arr_size; ++i){
            infile >> val(f, i);
            infile >> delim;
        }
    }
    infile.close();

    search(data, num_files, arr_size);
    delete[] data;

    std::exit(0);
}
