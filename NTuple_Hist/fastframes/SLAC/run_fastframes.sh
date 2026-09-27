#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_date=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
asetup StatAnalysis,0.6.2

cd /sdf/data/atlas/u/qlei/FastFramesTutorial/TutorialClass/build || exit

# shellcheck disable=SC1091
source setup.sh

cd - || exit
setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

if [ -x /usr/bin/time ]; then
  TIME_CMD=(/usr/bin/time -v)
  bench_mode=time_v
else
  TIME_CMD=()
  bench_mode=none
fi

# No cat needed here: the log IS the tee'd pipe output, so time -v's
# report is already in it.
"${TIME_CMD[@]}" python3 /srv/FastFramesTutorial/FastFrames/python/FastFrames.py -c /sdf/data/atlas/u/qlei/input_ff/mc20e_example_config.yml 2>&1 | tee fastframes.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

{
  hostname
  du example_FS.root
} >> fastframes.log

file_dir="/sdf/data/atlas/u/qlei/benchmarks/${curr_date}/FastFrames_Hist/"

mkdir -p "${file_dir}"

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${file_dir}/hostname.txt"

append_benchmark fastframes.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

mv fastframes.log "${file_dir}"
