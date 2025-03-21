cmake_minimum_required(VERSION 3.15)
project(test_plugin CXX)

find_package(openfx CONFIG REQUIRED)


set(CMAKE_VERBOSE_MAKEFILE on)
add_ofx_plugin(test_plugin .)
target_sources(test_plugin PRIVATE test_plugin.cpp)
target_link_libraries(test_plugin openfx::openfx)
