#!/bin/bash

source "${GITHUB_WORKSPACE}/parsing/utils/benchmark_utils.sh"

# shellcheck disable=SC2034
OS_container="centos7"

# The seed used in the job
# shellcheck disable=SC2034
seed=1001

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_epoch=$(date -u +%s)

# Directory storing the input files
config_dir="${GITHUB_WORKSPACE}/EVNT/EVNTFiles/100xxx/100001"

# Creates the ATLAS Environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Gen_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container

# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c centos7 -r "asetup AthGeneration,23.6.31,here &&\ 
  export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current &&\ 
  export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current &&\ 
  /usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig=${config_dir} --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=1001 2>&1 | tee pipe_file.log &&\
  cat pipe_file.log >> log.generate"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
end_epoch=$(date -u +%s)
wall_time=$((end_epoch - start_epoch))

# Appends time after Gen_tf.py to a log file
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du EVNT.root
} >> split.log

append_benchmark "log.generate" "${start_time}" "${wall_time}" "${end_time}" "time_v"
