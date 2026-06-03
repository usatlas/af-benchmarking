#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# The seed used in the job
seed=1001

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up our working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh

# Sets up the Ath* version
asetup AthGeneration,23.6.34,here

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time before Gen_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

/usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig=/atlasgpfs01/usatlas/data/qlei/EVNTJob/100xxx/100001/ --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=${seed} 2>&1 | tee pipe_file.log
cat pipe_file.log >> log.generate

# Appends time after Gen_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/EVNT_native_batch/${start_time}"

# Creates the output directory
mkdir -p "${output_dir}"
# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log

append_benchmark log.generate "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Checks the directory, if it matches it cleans it for the next job
if [ "$(pwd)" = "/usatlas/u/qlei/EVNT/native" ]; then
  rm -r ./*
fi
