cmake_minimum_required(VERSION 3.15)
project(PackageTest CXX)

find_package(shiboken2 CONFIG REQUIRED)

get_target_property(SHIBOKEN_LIB_DIRS shiboken2::libshiboken2 INTERFACE_LINK_DIRECTORIES)

set(SHIBOKEN_EXE shiboken2::shiboken2bin)
if(NOT TARGET shiboken2::shiboken2bin)
    message("\n\nSetting up shiboken2::shiboken2bin target\n")
    add_executable(shiboken2::shiboken2bin IMPORTED GLOBAL)
    set_target_properties(shiboken2::shiboken2bin PROPERTIES IMPORTED_LOCATION "${SHIBOKEN2_BIN}")
else()
    message("\n\nshiboken2::shiboken2bin already defined\n")
endif()

set(PY_TEST_HEADER src/py_test_python.h)
set(PyTestObj_SOURCES Qt5/Test/test_module_wrapper.cpp Qt5/Test/testobject_wrapper.cpp)
add_library(test_object_lib STATIC ${PY_TEST_HEADER} src/test_object.h src/test_object.cpp)
target_include_directories(test_object_lib PUBLIC src)


set(PyTestObj_OUT ${CMAKE_CURRENT_BINARY_DIR}/Qt${QT_VERSION_MAJOR})
set(TEST_TYPESYSTEM "src/typesystem_test.xml")
set(shiboken_args
    "-std=c++17" "--enable-parent-ctor-heuristic" "--use-isnull-as-nb_nonzero"
    "--avoid-protected-hack"
    "-I." "-I.." "-Isrc" "--output-directory=${PyTestObj_OUT}"
    ${PY_TEST_HEADER}
    "${TEST_TYPESYSTEM}")

add_custom_command(OUTPUT ${PyTestObj_SOURCES}
    COMMAND echo CONFIG $<CONFIG>
    COMMAND set
    COMMAND $<TARGET_FILE:${SHIBOKEN_EXE}> ${shiboken_args}
    COMMAND_EXPAND_LISTS
    VERBATIM
    DEPENDS ${SHIBOKEN_EXE} ${PY_TEST_HEADER} ${TEST_TYPESYSTEM}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})

add_library(test_object_pylib ${PyTestObj_SOURCES})
target_link_libraries(test_object_pylib shiboken2::libshiboken2 test_object_lib)

add_executable(test_object_main src/main.cpp )
target_link_libraries(test_object_main test_object_lib)