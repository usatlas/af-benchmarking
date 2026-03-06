#!/bin/bash

# Time that will be used to store the log file
curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh

asetup StatAnalysis,0.6.3
date +"%Y.%m.%d.%H.%M.%S" >> split.log &&\
python3 ~/AF-Benchmarking/NTuple_Hist/event_loop/BNL/standard/eventloop_noarrays.py 2>&1 | tee eventloop_noarrays.log

{
  date +"%Y.%m.%d.%H.%M.%S"
  hostname
  du event_loop_noarrays_output_hist.root
} >> split.log


output_dir="/atlasgpfs01/usatlas/data/jroblesgo/benchmarks/${curr_time}/eventloop_noarrays/"

mkdir -p "${output_dir}"

mv eventloop_noarrays.log "${output_dir}"
mv split.log "${output_dir}"
