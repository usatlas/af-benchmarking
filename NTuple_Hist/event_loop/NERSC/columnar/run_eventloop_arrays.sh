#!/bin/bash

curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Run this in a container

cd /pscratch/sd/s/selbor/ntuple/eventloop_arrays/ || exit

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  asetup StatAnalysis,0.6.2 &&\
  python3 ~/AF-Benchmarking/event_loop/NERSC/columnar/event_loop_arrays.py 2>1| tee eventloop_arrays.log"

{
  date -u +"%Y-%m-%dT%H:%M:%SZ"
  hostname
  du event_loop_arrays_output_hist.root
} >> split.log

output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/eventloop_arrays/"

mkdir -p "${output_dir}"

mv eventloop_arrays.log "${output_dir}"
mv split.log "${output_dir}"
