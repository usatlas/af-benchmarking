#!/bin/bash

# Current time used for log file storage
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defining the OS wanted in the container
OS_container="el9"

# The seed used in the job
seed=1001

# Directory storing the input files
config_dir="evnt_el9/100xxx/100001"

cd "$SCRATCH"/EVNT/el9/ || exit
cp -r "$HOME"/evnt_el9/ .
# Setting up the working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c ${OS_container} -m /global/cfs/cdirs/m2616/selbor -r "asetup AthGeneration,23.6.34,here && \
  date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log &&\
  Gen_tf.py --ecmEnergy=13000.0 --jobConfig=${config_dir}  --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=${seed} 2>&1 | tee pipe_file.log &&\
  date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log"

rm -r evnt_el9/

# Defines and makes the output directory
output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/EVNT_el9/"
mkdir -p "${output_dir}"

# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"


rm ./*
