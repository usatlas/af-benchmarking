#!/bin/bash
# shellcheck disable=SC1091

source ./parsing/utils/benchmark_utils.sh

# The ntuples are staged by the caller since their location differs per site
: "${NTUPLE_DIR:?Set NTUPLE_DIR to the directory holding the mc20e ntuples}"

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Getting start date
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Running the script
# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory (the ntuples may live outside $HOME)
## -r : precedes the commands we want to run within the container
# NTUPLE_DIR is expanded on the host and exported again inside, because the
# container is started with a clean environment (apptainer exec -e)
echo "::group::EventLoop Execution"
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m "${NTUPLE_DIR}" -r "lsetup 'views LCG_107a_ATLAS_2 x86_64-el9-gcc13-opt' && \
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log && \
  export NTUPLE_DIR='${NTUPLE_DIR}' && \
  /usr/bin/time -v python3 ./NTuple_Hist/event_loop/UC-ODF/standard/event_loop_noarrays.py 2>&1 | tee eventloop_noarrays.log"
echo "::endgroup::"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Collect metrics
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
hostname >> split.log
echo "::endgroup::"

append_benchmark "eventloop_noarrays.log" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
