cmake_minimum_required(VERSION 3.16.3)
project(shapes)

set (CMAKE_CXX_STANDARD 17)

# Add main source dir
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/math_funcs)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/geometry)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/primitives)

# Add a shared library for C++ source
file(GLOB_RECURSE SHAPES_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)
add_library(shapes SHARED ${SHAPES_SOURCES})

# Add wrapper dir
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/wrapper/)

# Add PyBind and Python headers
set(PYBIND11_PYTHON_VERSION 3)
set(PYBIND11_CPP_STANDARD -std=c++17)
add_subdirectory(wrapper/pybind11)
include_directories(${PYTHON_INCLUDE_DIRS})

# Copy the Python source and test trees to the build location
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/src/python/pyshapes DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/)
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/src/python/test/ DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/)

# Add the autogenerated files to the module target
file(GLOB MODULE_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/wrapper/math_funcs/*.cpp)
add_library(_pyshapes_math_funcs SHARED ${MODULE_SOURCES})
target_link_libraries(_pyshapes_math_funcs PRIVATE pybind11::module shapes)
file(GLOB MODULE_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/wrapper/geometry/*.cpp)
add_library(_pyshapes_geometry SHARED ${MODULE_SOURCES})
target_link_libraries(_pyshapes_geometry PRIVATE pybind11::module shapes)
file(GLOB MODULE_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/wrapper/primitives/*.cpp)
add_library(_pyshapes_primitives SHARED ${MODULE_SOURCES})
target_link_libraries(_pyshapes_primitives PRIVATE pybind11::module shapes)

# Set suitable extensions and put the module into a suitable location in the package
set_target_properties(_pyshapes_math_funcs PROPERTIES PREFIX "${PYTHON_MODULE_PREFIX}"
                                         SUFFIX "${PYTHON_MODULE_EXTENSION}" 
                                         LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pyshapes/math_funcs/)

set_target_properties(_pyshapes_geometry PROPERTIES PREFIX "${PYTHON_MODULE_PREFIX}"
                                         SUFFIX "${PYTHON_MODULE_EXTENSION}" 
                                         LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pyshapes/geometry/)

set_target_properties(_pyshapes_primitives PROPERTIES PREFIX "${PYTHON_MODULE_PREFIX}"
                                         SUFFIX "${PYTHON_MODULE_EXTENSION}" 
                                         LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pyshapes/primitives/)