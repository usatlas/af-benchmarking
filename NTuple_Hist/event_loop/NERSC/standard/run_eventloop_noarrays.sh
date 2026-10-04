#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Run this in a container

cd "$SCRATCH"/ntuple/eventloop_noarrays/ || exit

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# setup_end and the time -v mode can only be known inside the container, so
# they are written to split.log there and read back after it exits.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  asetup StatAnalysis,0.6.2 &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  if [ -x /usr/bin/time ]; then TIME_CMD='/usr/bin/time -v'; BENCH_MODE=time_v; else TIME_CMD=''; BENCH_MODE=none; fi &&\
  echo \"BENCH_MODE=\${BENCH_MODE}\" >> split.log &&\
  \${TIME_CMD} python3 ~/AF-Benchmarking/NTuple_Hist/event_loop/NERSC/standard/event_loop_noarrays.py 2>&1 | tee eventloop_noarrays.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
bench_mode=$(grep "^BENCH_MODE=" split.log 2>/dev/null | tail -1 | sed 's/^BENCH_MODE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du event_loop_noarrays_output_hist.root
} >> split.log

output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/eventloop_noarrays/"

mkdir -p "${output_dir}"

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

append_benchmark eventloop_noarrays.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode:-none}"

mv eventloop_noarrays.log "${output_dir}"
mv split.log "${output_dir}"
