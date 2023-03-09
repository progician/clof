cmake_minimum_required(VERSION 3.21)
project(TestBed)

add_library(TestBed test.cpp)
target_include_directories(TestBed PRIVATE libx/include)