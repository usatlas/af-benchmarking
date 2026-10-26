#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# Current time used for file storage

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")


# Defines the OS the container will have
OScontainer="el9"
job_dir="$SCRATCH/TRUTH3/el9/"
mkdir -p "${job_dir}"
cd "${job_dir}" || exit

# A run killed before its final mv leaves split.log behind; clear it so a
# stale SETUP_COMPLETE line cannot mask this run's failed setup.
rm -f split.log

cp ~/AF-Benchmarking/TRUTH3/EVNT.root .
# Sets up the working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Reco_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
#
# ALRB evaluates the -r string once, before running any of it, so it holds
# no runtime $: date prints the SETUP_COMPLETE label itself rather than being
# wrapped in $(date). setup_end is written to split.log inside the container
# and read back after it exits.
# time -v's report lands in the tee'd pipe, not in the transform's own log,
# so the chain folds pipe_file.log into it for append_benchmark to read.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c "${OScontainer}" -m /global/cfs/cdirs/m2616/qlei -r "asetup Athena,24.0.53,here && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.Derivation"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time after Reco_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

rm EVNT.root

# Defines the output directory
output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/TRUTH3_el9_container"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

# A failed release setup never reaches the payload, so there is no time -v
# report to read; record the failure explicitly instead.
bench_mode=time_v
# shellcheck disable=SC2034 # read by append_benchmark
[ -n "${setup_end}" ] || { bench_mode=none; BENCH_EXIT_STATUS=1; }

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

# Moves the log file to the output directory
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
