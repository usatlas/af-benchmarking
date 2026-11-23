#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# Input format: ttree (default) or rntuple. Each format gets its own working
# directory (split.log, output histogram), log name and log directory, so the
# two jobs never share files, even when they run at the same time.
format="${1:-ttree}"
case "${format}" in
  ttree) variant_suffix="" ;;
  rntuple) variant_suffix="_rntuple" ;;
  *)
    echo "unknown format: ${format} (expected ttree or rntuple)" >&2
    exit 2
    ;;
esac
log_file="eventloop_noarrays${variant_suffix}.log"

working_dir="/atlasgpfs01/usatlas/data/qlei/ntuple/eventloop_noarrays${variant_suffix}"
mkdir -p "${working_dir}"
cd "${working_dir}" || exit

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh

asetup StatAnalysis,0.7.3

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log &&\
/usr/bin/time -v python3 ~/AF-Benchmarking/NTuple_Hist/event_loop/BNL/standard/eventloop_noarrays.py --format "${format}" 2>&1 | tee "${log_file}"

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du event_loop_noarrays_output_hist.root
} >> split.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

output_dir="/atlasgpfs01/usatlas/data/qlei/logs/eventloop_noarrays${variant_suffix}/${start_time}"

mkdir -p "${output_dir}"

append_benchmark "${log_file}" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"

mv "${log_file}" "${output_dir}"
mv split.log "${output_dir}"
