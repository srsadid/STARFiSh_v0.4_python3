cmake_minimum_required(VERSION 3.15)
project(crimson_starfish_bridge)

# 1. Set up Python and nanobind
find_package(Python 3.8 REQUIRED COMPONENTS Interpreter Development.Module)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import nanobind; print(nanobind.cmake_dir())"
    OUTPUT_VARIABLE nanobind_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
find_package(nanobind CONFIG REQUIRED)

# 2. Define CRIMSON and Dependency Paths
set(CRIMSON_ROOT "/home/sadid/crimson/cfs_reg/CRIMSONFlowsolver")
set(CRIMSON_DEPS "/home/sadid/crimson/deps/installs")
# This is where your .a files live
set(CRIMSON_LIB_DIR "${CRIMSON_ROOT}/lib")

# 3. Include Directories 
# (Needed so the compiler understands CRIMSON types in your Bridge code)
include_directories(
    ${CRIMSON_ROOT}/flowsolver/src
    ${CRIMSON_ROOT}/estimation/src
    ${CRIMSON_ROOT}/solverio/src
    ${CRIMSON_ROOT}/utils/src
    ${CRIMSON_ROOT}/common/src
    ${CRIMSON_ROOT}/gtest-1.7.0/include
    
    ${CRIMSON_DEPS}/petsc/include
    ${CRIMSON_DEPS}/boost_1_74/include
    ${CRIMSON_DEPS}/openblas/include
    ${CRIMSON_DEPS}/vtk-crimson/include/vtk-5.8
)

# 4. Build the Python module from your Bridge files ONLY
# We do NOT include .cxx files here because we link the .a libs instead
nanobind_add_module(crimson_starfish_bridge 
    bindings.cpp 
    StarfishBridge.cpp
)

# 5. Force the bridge to use Real scalars to match CRIMSON's core
target_compile_definitions(crimson_starfish_bridge PRIVATE PETSC_USE_REAL_SCALAR)

# 6. Link everything together
# We link the .a libraries which contain all the symbols (NetlistReader, etc.)
target_link_libraries(crimson_starfish_bridge PRIVATE 
    # CRIMSON Static Libraries (order can matter, specialized first)
    ${CRIMSON_LIB_DIR}/libcrimson_flowsolver.a
    ${CRIMSON_LIB_DIR}/libcrimson_solverio.a
    ${CRIMSON_LIB_DIR}/libcrimson_common.a
    
    # External Dependencies
    ${CRIMSON_DEPS}/petsc/lib/libpetsc.so
    ${CRIMSON_DEPS}/openblas/lib/libopenblas.so
    ${CRIMSON_DEPS}/boost_1_74/lib/libboost_system.so
    ${CRIMSON_DEPS}/boost_1_74/lib/libboost_filesystem.so
    ${CRIMSON_DEPS}/boost_1_74/lib/libboost_thread.so
)