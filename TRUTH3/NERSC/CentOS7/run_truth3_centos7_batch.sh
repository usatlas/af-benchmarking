#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# current time used for log file storage


curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defines the OS the container will have
OScontainer="centos7"
job_dir="$SCRATCH/TRUTH3/centos7/"
mkdir -p "${job_dir}"
cd "${job_dir}" || exit
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
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c "${OScontainer}" -m /global/cfs/cdirs/m2616/qlei -r "asetup AthDerivation,21.2.178.0,here && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v Reco_tf.py --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --reductionConf TRUTH3 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.EVNTtoDAOD"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time after Reco_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

rm EVNT.root

# Defining the output directory
output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/TRUTH3_centos/"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

append_benchmark log.EVNTtoDAOD "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" time_v

# Moves the log file to the output directory
mv log.EVNTtoDAOD "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
