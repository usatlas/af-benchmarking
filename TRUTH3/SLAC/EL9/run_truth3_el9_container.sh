#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# Defines the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time before Derivation_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
asetup Athena,24.0.53,here
setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# /usr/bin/time -v may not exist in every ALRB container -- guard rather
# than assume, so append_benchmark is never asked to extract metrics from
# output that was never produced.
if [ -x /usr/bin/time ]; then
  TIME_CMD=(/usr/bin/time -v)
  bench_mode=time_v
else
  TIME_CMD=()
  bench_mode=none
fi

"${TIME_CMD[@]}" Derivation_tf.py --CA True --inputEVNTFile /sdf/data/atlas/u/qlei/TRUTH3Files/el/EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

# time -v's report lands in the tee'd pipe, not in Derivation_tf.py's own
# log.Derivation -- fold it in so append_benchmark can read it.
cat pipe_file.log >> log.Derivation

# Appends time after Derivation_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defines the output directory where the log file will be stored
output_dir="/sdf/data/atlas/u/$USER/benchmarks/${curr_time}/TRUTH3_el9_container"

# Creates the output directory
mkdir -p "${output_dir}"
# Appends the host-name to the end of the log file
hostname >> split.log
# Appends the size of the output DAOD file to the end of the log file
du DAOD_TRUTH3.TRUTH3.root >> split.log

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${output_dir}/hostname.txt"

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

# Moves the log file to the output directory defined above
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
