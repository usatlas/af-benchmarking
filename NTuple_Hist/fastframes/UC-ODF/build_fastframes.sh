#!/bin/bash
# shellcheck disable=SC1091

# Builds FastFrames and the TutorialClass custom frame inside an el9 container
# with StatAnalysis 0.6.3, following FastFrames' docs/tutorial.md. UC runs the
# job from a prebuilt tree that cannot be reused elsewhere, because CMake
# records absolute paths in the build tree and in the RPATH.
#
# Usage: FF_DIR=/path/to/FastFramesTutorial ./build_fastframes.sh
# FF_DIR holds the FastFrames/ and TutorialClass/ source trees. The libraries
# are installed under FF_DIR/install and FF_DIR/TutorialClass/install.
# JOBS sets the compile parallelism (default 1): the C++ templates in
# RDataFrame code can need several GB per compiler process.

: "${FF_DIR:?Set FF_DIR to the FastFramesTutorial directory holding FastFrames/ and TutorialClass/}"
jobs="${JOBS:-1}"

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory (FF_DIR may live outside $HOME)
## -r : precedes the commands we want to run within the container
# FF_DIR and jobs are expanded on the host because the container starts with a
# clean environment (apptainer exec -e). The final ls fails if the custom
# frame library was not installed.
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m "${FF_DIR}" -r "asetup StatAnalysis,0.6.3 && \
  cd '${FF_DIR}' && \
  cmake -S FastFrames -B build -DCMAKE_INSTALL_PREFIX='${FF_DIR}/install' -DPython3_EXECUTABLE=\$(which python3) && \
  cmake --build build -j${jobs} --target install && \
  mkdir -p TutorialClass/build && cd TutorialClass/build && \
  cmake -DCMAKE_PREFIX_PATH='${FF_DIR}/install' -DCMAKE_INSTALL_PREFIX='${FF_DIR}/TutorialClass/install' ../ && \
  cmake --build . -j${jobs} --target install && \
  ls -l '${FF_DIR}/TutorialClass/install/lib/libTutorialClass.so'"
