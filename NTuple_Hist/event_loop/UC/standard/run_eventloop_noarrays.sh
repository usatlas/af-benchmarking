#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# Input format: ttree (default) or rntuple. It picks the dataset copy and the
# log name, so the two formats' benchmarks are reported separately.
format="${1:-ttree}"
case "${format}" in
  ttree) log_file=eventloop_noarrays.log ;;
  rntuple) log_file=eventloop_noarrays_rntuple.log ;;
  *)
    echo "unknown format: ${format} (expected ttree or rntuple)" >&2
    exit 2
    ;;
esac

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"
lsetup "views LCG_107a_ATLAS_2 x86_64-el9-gcc13-opt"

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Getting start date
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Running the script
echo "::group::EventLoop Execution"
/usr/bin/time -v python3 ./NTuple_Hist/event_loop/UC/standard/event_loop_noarrays.py --format "${format}" 2>&1 | tee "${log_file}"
echo "::endgroup::"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Collect metrics
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
hostname >> split.log
echo "::endgroup::"

append_benchmark "${log_file}" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
