#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# Current time used for log file storage
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

OS_container="centos7"

# The seed used in the job
seed=1001

# Directory storing the input files
config_dir="evnt_centos7/100xxx/100001"
cd "$SCRATCH"/EVNT/centos7/ || exit

# A run killed before its final mv leaves split.log behind; clear it so a
# stale SETUP_COMPLETE line cannot mask this run's failed setup.
rm -f split.log

cp -r "$HOME"/evnt_centos7/ .
# Creates the ATLAS Environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

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
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c ${OS_container} -m /global/cfs/cdirs/m2616/qlei -r "asetup AthGeneration,23.6.31,here && \
  export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && \
  export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig=${config_dir} --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=${seed} 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.generate"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

rm -r evnt_centos7/

# Defines and makes the output directory
output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/EVNT_centos7/"
mkdir -p "${output_dir}"

# Appends the hostname and payload size to the log files
hostname >> split.log
du EVNT.root >> split.log

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

# A failed release setup never reaches the payload, so there is no time -v
# report to read; record the failure explicitly instead.
bench_mode=time_v
# shellcheck disable=SC2034 # read by append_benchmark
[ -n "${setup_end}" ] || { bench_mode=none; BENCH_EXIT_STATUS=1; }

append_benchmark log.generate "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
