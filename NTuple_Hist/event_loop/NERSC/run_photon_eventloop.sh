#!/bin/bash

# Time that will be used to store the log file
curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Job directory
cd /pscratch/sd/s/selbor/ntuple/event_loop || exit

# Setting up
setup ATLAS

# Setting up root
export ALRB_rootVersion=6.34.04-x86_64-el9-gcc13-opt
lsetup root

# Getting start date
date -u +"%Y-%m-%dT%H:%M:%SZ" >> photon_eventloop.log

# Running the script
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c centos7 -r "lsetup 'python 3.9.21-x86_64-centos7' &&\
  python3 ~/AF-Benchmarking/event_loop/NERSC/photon_ABCD_eventloop.py 2>&1 | tee photon_eventloop.log"

# Getting end date
date -u +"%Y-%m-%dT%H:%M:%SZ" >> photon_eventloop.log

# Getting host name
hostname >> photon_eventloop.log

# Output Dir
output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/photon_eventloop/"

mkdir -p "${output_dir}"

mv photon_eventloop.log "${output_dir}"
