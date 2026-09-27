#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# Gets the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cp /sdf/home/q/qlei/AF-Benchmarking/NTuple_Hist/coffea/SLAC/example.py .

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

if [ -x /usr/bin/time ]; then
  TIME_CMD=(/usr/bin/time -v)
  bench_mode=time_v
else
  TIME_CMD=()
  bench_mode=none
fi

# The default ALRB el9 container has no science Python stack -- awkward,
# coffea, dask, etc. are installed once via `installPip` into a persistent,
# relocatable location, and this setup.sh (which installPip generates) is
# what puts them on PYTHONPATH.
# shellcheck disable=SC1091
source /sdf/data/atlas/u/qlei/coffea_pip/setup.sh

# No cat needed here: the log IS the tee'd pipe output, so time -v's
# report is already in it.
"${TIME_CMD[@]}" python3 example.py 2>&1 | tee coffea_hist.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

log_file_dir="/sdf/data/atlas/u/qlei/benchmarks/${curr_time}/Coffea_Hist/"

mkdir -p "${log_file_dir}"

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${log_file_dir}/hostname.txt"

# No separate setup phase to time here (the installPip source above is
# fast -- it's just PYTHONPATH/PATH exports, not a real install step on
# every run) -- setupTime comes out as 0.
append_benchmark coffea_hist.log "${start_time}" "${end_time}" "${curr_time}" "${curr_time}" "${bench_mode}"

mv coffea_hist.log "${log_file_dir}"
mv split.log "${log_file_dir}"
