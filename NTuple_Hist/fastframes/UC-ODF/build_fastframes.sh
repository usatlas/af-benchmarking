#!/bin/bash
# shellcheck disable=SC1091

# Builds FastFrames and the TutorialClass custom frame inside an el9 container
# with StatAnalysis 0.6.3, following FastFrames' docs/tutorial.md. UC runs the
# job from a prebuilt tree that cannot be reused elsewhere, because CMake
# records absolute paths in the build tree and in the RPATH.
#
# Usage: FF_DIR=/path/to/FastFramesTutorial ./build_fastframes.sh
# FF_DIR receives the FastFrames and TutorialClass sources (see
# fetch_fastframes_sources.sh). The libraries are installed under
# FF_DIR/install and FF_DIR/TutorialClass/install. Run again on an existing
# tree, only what changed is rebuilt.
# JOBS sets the compile parallelism (default 1): the C++ templates in
# RDataFrame code can need several GB per compiler process.
# BUILD_LOCK_TIMEOUT is how many seconds to wait for another build (default 3600).

: "${FF_DIR:?Set FF_DIR to the directory to build the FastFramesTutorial tree in}"
jobs="${JOBS:-1}"
lock_timeout="${BUILD_LOCK_TIMEOUT:-3600}"

command -v flock > /dev/null || { echo "flock (util-linux) is required" >&2; exit 1; }

# Runs share this volume, so only one may fetch and build at a time; the others
# wait here and then find the tree already built. The lock is released when
# this script exits, even if it is killed.
mkdir -p "${FF_DIR}"
exec 9>> "${FF_DIR}/.build.lock"
if ! flock -w "${lock_timeout}" 9; then
  echo "Timed out after ${lock_timeout}s waiting for another FastFrames build in ${FF_DIR}" >&2
  exit 1
fi

# Fetched on the host, which is where the network access is
"$(dirname -- "${BASH_SOURCE[0]}")"/fetch_fastframes_sources.sh || exit 1

export ATLAS_LOCAL_ROOT_BASE="${ATLAS_LOCAL_ROOT_BASE:-/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase}"

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
