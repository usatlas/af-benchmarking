#!/bin/bash

config_dir="EVNTFiles/100xxx/100001/"

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# No rm -r ./* here: the cron wrapper already cleans this directory
# (cd $HOME/EVNTJob/container_centos || exit; rm ./*) before calling
# sbatch.

# Copies input files dir to the working dir
cp -r "$HOME"/AF-Benchmarking/EVNT/EVNTFiles .

# Current time used for log file storage
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time before Gen_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
asetup AthGeneration,23.6.31,here

export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current

export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current

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

"${TIME_CMD[@]}" Gen_tf.py --ecmEnergy=13000.0 --jobConfig="${config_dir}" --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=1001 2>&1 | tee pipe_file.log

# time -v's report lands in the tee'd pipe, not in Gen_tf.py's own
# log.generate -- fold it in so append_benchmark can read it.
cat pipe_file.log >> log.generate

# Appends time after Gen_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defines the output directory
output_dir="/sdf/data/atlas/u/$USER/benchmarks/${curr_time}/EVNT_container_centos"
# Creates the output directory
mkdir -p "${output_dir}"
# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${output_dir}/hostname.txt"

append_benchmark log.generate "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

# Moves the log file and date_name file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
