#!/bin/bash

source /usatlas/u/qlei/dev/af-benchmarking/parsing/utils/benchmark_utils.sh

# Current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_epoch=$(date -u +%s)

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c centos7 -m /atlasgpfs01 -r "asetup AthGeneration,23.6.31,here && export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current &&\
  echo $(date -u "+%Y-%m-%dT%H:%M:%SZ") >> split.log &&\
  /usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig=/atlasgpfs01/usatlas/data/qlei/EVNTJob/100xxx/100001/ --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=1001 2>&1 | tee pipe_file.log &&\
  cat pipe_file.log >> log.generate &&\
  echo $(date -u "+%Y-%m-%dT%H:%M:%SZ") >> split.log"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
end_epoch=$(date -u +%s)
wall_time=$((end_epoch - start_epoch))

# Output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/EVNT_centos7_batch/${start_time}"

# Creates the output directory
mkdir -p "${output_dir}"
# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log

append_benchmark log.generate "${start_time}" "${wall_time}" "${end_time}" "time_v"

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Checks the directory, if it matches it cleans it for the next job
if [ "$(pwd)" = "/usatlas/u/qlei/test/EVNT/centos" ]; then
  rm -r ./*
fi
