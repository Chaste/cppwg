cmake_minimum_required(VERSION 2.8.12)
project(example)

set (CMAKE_CXX_STANDARD 11)

# Add main source dir
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/example_project)
# Add wrapper dir
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/wrap_simple_function)

# Add PyBind and Python headers
set(PYBIND11_PYTHON_VERSION 2.7)
set(PYBIND11_CPP_STANDARD -std=c++11)
add_subdirectory(external/pybind11)
include_directories(${PYTHON_INCLUDE_DIRS})

# Copy the Python source and test trees to the build location
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/example_project/python/ DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/)
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/example_project/test/ DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/)

# The module is built using the wrapper code 'main' source files
add_library(_py_example_project_functions SHARED ${CMAKE_CURRENT_SOURCE_DIR}/wrap_simple_function/functions/functions.main.cpp)

# Link with PyBind
target_link_libraries(_py_example_project_functions PRIVATE pybind11::module)

# Set suitable extensions and put the module into a suitable location in the package
set_target_properties(_py_example_project_functions PROPERTIES PREFIX "${PYTHON_MODULE_PREFIX}"
                                         SUFFIX "${PYTHON_MODULE_EXTENSION}" 
                                         LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/py_example_project/functions/)