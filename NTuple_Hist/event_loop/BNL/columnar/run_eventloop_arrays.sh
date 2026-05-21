#!/bin/bash

# shellcheck disable=SC1091
source /usatlas/u/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
asetup StatAnalysis,0.6.3

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
/usr/bin/time -v python3 ~/AF-Benchmarking/NTuple_Hist/event_loop/BNL/columnar/eventloop_arrays.py 2>&1 | tee eventloop_arrays.log

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du event_loop_output_hist.root
} >> split.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

output_dir="/atlasgpfs01/usatlas/data/qlei/logs/eventloop_arrays/${start_time}"

mkdir -p "${output_dir}"

echo "Start Time: ${start_time}"
echo "End Time: ${end_time}"

# Verify the log exists before appending
if [ -f eventloop_arrays.log ]; then
  append_benchmark eventloop_arrays.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
else
  echo "ERROR: eventloop_arrays.log not found in $(pwd)"
fi

# append_benchmark eventloop_arrays.log "${start_time}" "${end_time}"

mv eventloop_arrays.log "${output_dir}"
mv split.log "${output_dir}"
