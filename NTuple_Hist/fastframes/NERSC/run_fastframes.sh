#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_date=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cd /global/cfs/cdirs/m2616/qlei/ || exit

# Sets up ATLAS environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# ALRB evaluates the -r string once, before running any of it, so it holds
# no runtime $: date prints the SETUP_COMPLETE label itself rather than being
# wrapped in $(date). setup_end is written to split.log inside the container
# and read back after it exits.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -m /global/cfs/cdirs/m2616/qlei/ -c el9 -r "asetup StatAnalysis,0.6.2 && \
  source /srv/FastFramesTutorial/TutorialClass/build/setup.sh && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v python3 /srv/FastFramesTutorial/FastFrames/python/FastFrames.py -c /srv/fastframes_input/mc20e_example_config.yml 2>&1 | tee fastframes.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

hostname >> fastframes.log

du example_FS.root >> fastframes.log

# output directory
output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/$curr_date/FastFrames_NTuple"

# Creates output dir
mkdir -p "${output_dir}"

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

# A failed release setup never reaches the payload, so there is no time -v
# report to read; record the failure explicitly instead.
bench_mode=time_v
# shellcheck disable=SC2034 # read by append_benchmark
[ -n "${setup_end}" ] || { bench_mode=none; BENCH_EXIT_STATUS=1; }

append_benchmark fastframes.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

# Moves log to outputdir
mv fastframes.log "${output_dir}"
# split.log only carries the in-container markers; move it so it does not
# accumulate in the shared CFS working directory between runs.
mv split.log "${output_dir}"
