cmake_minimum_required(VERSION 3.16)
project(TestCppProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find packages
find_package(Boost REQUIRED)
find_package(GTest REQUIRED)

# Add executable
add_executable(test_cpp TestCpp.cpp)

# Link libraries
target_link_libraries(test_cpp
    Boost::boost
    GTest::gtest_main
)

# Include directories
target_include_directories(test_cpp PRIVATE
    ${Boost_INCLUDE_DIRS}
)