# Set the minimum CMake version required to build the project.
cmake_minimum_required( VERSION 3.10 )

# Silence some warnings on macOS with new CMake versions.
if( NOT ${CMAKE_VERSION} VERSION_LESS 3.9 )
   cmake_policy( SET CMP0068 NEW )
endif()

set(CMAKE_INSTALL_PREFIX "" CACHE PATH "Path to the install directory")
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")

# Set the project's name and version.
project( TutorialClass )

# Set up the "C++ version" to use.
set( CMAKE_CXX_STANDARD_REQUIRED 17 CACHE STRING
   "Minimum C++ standard required for the build" )
set( CMAKE_CXX_STANDARD 17 CACHE STRING
   "C++ standard to use for the build" )
set( CMAKE_CXX_EXTENSIONS FALSE CACHE BOOL
   "(Dis)allow using compiler extensions" )

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Specify the install locations for libraries and binaries.
set( CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin )
set( CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib )
set( CMAKE_INSTALL_LIBDIR ${CMAKE_BINARY_DIR}/lib )  # Needed by ROOT_GENERATE_DICTIONARY()

# Set the warning flag(s) to use.
set( CMAKE_CXX_FLAGS "-Wall -Wextra -Wshadow -pedantic -O3 -g" )

set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)

# Silence boost warnings
add_definitions(-DBOOST_BIND_GLOBAL_PLACEHOLDERS)
add_definitions(-DBOOST_ALLOW_DEPRECATED_HEADERS)

# Add ROOT system directory and require ROOT.
find_package( ROOT 6.36.00 REQUIRED COMPONENTS Core Hist RIO Tree ROOTDataFrame ROOTVecOps)

find_package( FastFrames REQUIRED )

file(GLOB SOURCES "Root/*.cc")
file(GLOB LIB_HEADERS "TutorialClass/*.h")
if ( NOT ONNXRUNTIME_ROOTDIR STREQUAL "")
   add_definitions(-DONNXRUNTIME_AVAILABLE)
endif()

# Build the shared library.
add_library( TutorialClass SHARED ${LIB_HEADERS} ${SOURCES} )
target_include_directories( TutorialClass PUBLIC $<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}> $<INSTALL_INTERFACE:> ${FastFrames_INCLUDE_DIRS} ${ROOT_INCLUDE_DIRS} ${ONNXRUNTIME_INCLUDE_DIRS})
find_library(FastFrames_LIBRARY FastFrames ${CMAKE_SOURCE_DIR}/install)
target_link_libraries( TutorialClass PRIVATE ${FastFrames_LIBRARY} ${ROOT_LIBRARIES} ${ONNXRUNTIME_LIBRARIES})
set_property( TARGET TutorialClass
   PROPERTY PUBLIC_HEADER ${LIB_HEADERS} )
target_include_directories(TutorialClass PUBLIC ${CMAKE_CURRENT_LIST_DIR} )
target_compile_options(TutorialClass PUBLIC -Wno-shadow)

set(SETUP ${CMAKE_CURRENT_BINARY_DIR}/setup.sh)
file(WRITE ${SETUP} "#!/bin/bash\n")
file(APPEND ${SETUP} "# this is an auto-generated setup script\n" )
file(APPEND ${SETUP} "export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}:${CMAKE_INSTALL_PREFIX}/lib\n")

# Install the libraries.
install( TARGETS TutorialClass
   EXPORT TutorialClassTargets
   ARCHIVE DESTINATION lib
   LIBRARY DESTINATION lib
   PUBLIC_HEADER DESTINATION include/TutorialClass )

ROOT_GENERATE_DICTIONARY(TutorialClass_dict TutorialClass/TutorialClass.h MODULE TutorialClass LINKDEF Root/LinkDef.h)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/lib/lib${PROJECT_NAME}_rdict.pcm ${CMAKE_CURRENT_BINARY_DIR}/lib/lib${PROJECT_NAME}.rootmap DESTINATION ${CMAKE_INSTALL_PREFIX}/lib)
