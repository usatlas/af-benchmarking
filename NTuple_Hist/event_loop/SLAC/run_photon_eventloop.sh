#!/bin/bash

# Time that will be used to store the log file
curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 


export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /sdf/data/usatlas/u/selbor/ -r "export ALRB_rootVersion=6.34.04-x86_64-el9-gcc13-opt && \
  lsetup root && \
  date >> photon_eventloop.log && \
  python3 ~/AF-Benchmarking/event_loop/SLAC/photon_ABCD_eventloop.py 2>&1 | tee photon_eventloop.log  && \
  date >> photon_eventloop.log && \
  hostname >> photon_eventloop.log"

# Output directory
output_dir="/sdf/home/s/selbor/benchmarks/${curr_time}/photon_eventloop/"

mkdir -p "${output_dir}"

mv photon_eventloop.log "${output_dir}"
