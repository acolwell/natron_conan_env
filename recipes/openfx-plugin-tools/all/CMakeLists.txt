cmake_minimum_required(VERSION 3.15)
project(openfx-plugin-tools CXX)

set(CMAKE_VERBOSE_MAKEFILE on)
set(CMAKE_CXX_STANDARD 11)

find_package(openfx REQUIRED CONFIG)
find_package(expat REQUIRED CONFIG)

if(MSVC)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DWINDOWS -DNOMINMAX")
else()
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wno-deprecated -Wno-deprecated-declarations")
endif()

add_executable(verify_openfx_plugin_loads src/verify_openfx_plugin_loads.cpp src/third_party/ofxhBinaryStrict.cpp)
target_link_libraries(verify_openfx_plugin_loads openfx::openfx)


install(TARGETS verify_openfx_plugin_loads DESTINATION "."
        RUNTIME DESTINATION bin
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        )
