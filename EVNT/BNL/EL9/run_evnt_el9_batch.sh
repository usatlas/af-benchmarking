#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# The OS used in the container
OScontainer="el9"

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c ${OScontainer} -m /atlasgpfs01 -r "asetup AthGeneration,23.6.34,here &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  echo $(date -u "+%Y-%m-%dT%H:%M:%SZ") >> split.log &&\
  /usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig=/atlasgpfs01/usatlas/data/qlei/EVNTJob/100xxx/100001/ --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=1001 2>&1 | tee pipe_file.log &&\
  cat pipe_file.log >> log.generate &&\
  echo $(date -u "+%Y-%m-%dT%H:%M:%SZ") >> split.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/EVNT_el9_batch/${start_time}"

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
if [ "$(pwd)" = "/usatlas/u/qlei/EVNT/el" ]; then
  rm -r ./*
fi
