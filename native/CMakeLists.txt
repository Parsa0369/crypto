cmake_minimum_required(VERSION 3.16)
project(cryptopulse_native LANGUAGES CXX)
add_library(cryptopulse_indicators STATIC indicators.cpp)
target_compile_features(cryptopulse_indicators PUBLIC cxx_std_17)
