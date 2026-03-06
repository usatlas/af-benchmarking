#!/bin/bash

curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 

# Run this in a container

cd /pscratch/sd/s/selbor/ntuple/eventloop_noarrays/ || exit

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  asetup StatAnalysis,0.6.2 &&\
  python3 ~/AF-Benchmarking/event_loop/NERSC/standard/event_loop_noarrays.py 2>1| tee eventloop_noarrays.log"

{
  date +"%Y.%m.%d.%H.%M.%S"
  hostname
  du event_loop_noarrays_output_hist.root
} >> split.log

output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/eventloop_noarrays/"

mkdir -p "${output_dir}"

mv eventloop_noarrays.log "${output_dir}"
mv split.log "${output_dir}"
