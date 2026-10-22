#!/bin/bash
# shellcheck disable=SC1091

source ./parsing/utils/benchmark_utils.sh
source ./NTuple_Hist/UC-ODF/ntuple_utils.sh

# Both are staged by the caller since their locations differ per site
require_ntuple_dir
: "${FF_DIR:?Set FF_DIR to the built FastFramesTutorial directory (see build_fastframes.sh)}"

# FastFrames is built once, by an administrator, and only run here
for built_file in FastFrames/python/FastFrames.py TutorialClass/build/setup.sh TutorialClass/install/lib/libTutorialClass.so; do
  if [[ ! -e "${FF_DIR}/${built_file}" ]]; then
    echo "FastFrames is not built in ${FF_DIR} (missing ${built_file}); build it with NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh" >&2
    exit 1
  fi
done

# Holds the generated file list and the histograms FastFrames writes
run_dir=./fastframes_run
mkdir -p "${run_dir}"
./NTuple_Hist/fastframes/UC-ODF/make_filelist.sh "${NTUPLE_DIR}" > "${run_dir}"/mc20e_filelist.txt || exit 1

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Getting start date
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts the directories holding the ntuples and the FastFrames build
## -r : precedes the commands we want to run within the container
# The directories are expanded on the host because the container starts with a
# clean environment (apptainer exec -e).
echo "::group::FastFrames"
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m "${NTUPLE_DIR},${FF_DIR}" -r "asetup StatAnalysis,0.6.3 && \
  source '${FF_DIR}/TutorialClass/build/setup.sh' && \
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log && \
  /usr/bin/time -v python3 '${FF_DIR}/FastFrames/python/FastFrames.py' -c ./NTuple_Hist/fastframes/UC-ODF/mc20e_example_config.yml 2>&1 | tee fastframes.log"
printf "\n"
echo "::endgroup::"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

append_benchmark "fastframes.log" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
