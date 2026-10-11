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
# setup_end and the time -v mode can only be known inside the container, so
# they are written to split.log there and read back after it exits.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c ${OS_container} -m /global/cfs/cdirs/m2616/qlei -r "source ${HOME}/AF-Benchmarking/EVNT/NERSC/CentOS7/evnt_centos7_container.sh ${config_dir} ${seed}"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
bench_mode=$(grep "^BENCH_MODE=" split.log 2>/dev/null | tail -1 | sed 's/^BENCH_MODE=//')
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

append_benchmark log.generate "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode:-none}"

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
