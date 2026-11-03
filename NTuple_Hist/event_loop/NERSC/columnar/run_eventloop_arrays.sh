#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Run this in a container

cd "$SCRATCH"/ntuple/eventloop_arrays/ || exit

# A run killed before its final mv leaves split.log behind; clear it so a
# stale SETUP_COMPLETE line cannot mask this run's failed setup.
rm -f split.log

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# ALRB evaluates the -r string once, before running any of it, so it holds
# no runtime $: date prints the SETUP_COMPLETE label itself rather than being
# wrapped in $(date). setup_end is written to split.log inside the container
# and read back after it exits.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "lsetup 'python 3.9.22-x86_64-el9' && \
  asetup StatAnalysis,0.6.2 && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v python3 ${HOME}/AF-Benchmarking/NTuple_Hist/event_loop/NERSC/columnar/event_loop_arrays.py 2>&1 | tee eventloop_arrays.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du event_loop_arrays_output_hist.root
} >> split.log

output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/eventloop_arrays/"

mkdir -p "${output_dir}"

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

# A failed release setup never reaches the payload, so there is no time -v
# report to read; record the failure explicitly instead.
bench_mode=time_v
# shellcheck disable=SC2034 # read by append_benchmark
[ -n "${setup_end}" ] || { bench_mode=none; BENCH_EXIT_STATUS=1; }

append_benchmark eventloop_arrays.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

mv eventloop_arrays.log "${output_dir}"
mv split.log "${output_dir}"
