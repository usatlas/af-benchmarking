#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

asetup StatAnalysis,0.6.2

# Time that will be used to store the log file
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

cp /sdf/home/q/qlei/AF-Benchmarking/NTuple_Hist/event_loop/SLAC/columnar/event_loop_arrays.py .

if [ -x /usr/bin/time ]; then
  TIME_CMD=(/usr/bin/time -v)
  bench_mode=time_v
else
  TIME_CMD=()
  bench_mode=none
fi

# No cat needed here: the log IS the tee'd pipe output, so time -v's
# report is already in it.
"${TIME_CMD[@]}" python3 event_loop_arrays.py 2>&1 | tee event_loop_arrays.log

# Getting end date
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Getting host name
{
  hostname
  du event_loop_arrays_output_hist.root
} >> split.log

output_dir="/sdf/data/atlas/u/qlei/benchmarks/${curr_time}/eventloop_arrays/"

mkdir -p "${output_dir}"

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${output_dir}/hostname.txt"

# No asetup timing captured here (asetup runs before start_time; there's
# no separate setup phase distinct from job start in the original script),
# so setupTime comes out as 0.
append_benchmark event_loop_arrays.log "${start_time}" "${end_time}" "${curr_time}" "${curr_time}" "${bench_mode}"

mv event_loop_arrays.log "${output_dir}"
mv split.log "${output_dir}"
