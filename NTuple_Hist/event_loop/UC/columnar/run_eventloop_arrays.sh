#!/bin/bash

source "${GITHUB_WORKSPACE}/parsing/utils/benchmark_utils.sh"

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"
lsetup "views LCG_107a_ATLAS_2 x86_64-el9-gcc13-opt"

# Getting start date
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Running the script
echo "::group::EventLoop Execution"
/usr/bin/time -v python3 "${GITHUB_WORKSPACE}"/NTuple_Hist/event_loop/UC/columnar/event_loop_arrays.py 2>&1 | tee eventloop_arrays.log
echo "::endgroup::"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Collect metrics
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
hostname >> split.log
echo "::endgroup::"

append_benchmark "eventloop_arrays.log" "${start_time}" "${end_time}" "time_v"
