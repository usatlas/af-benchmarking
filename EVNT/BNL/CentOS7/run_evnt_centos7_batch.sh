#!/bin/bash

# Current time used for log file storage
curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")


# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c centos7 -m /atlasgpfs01 -r "asetup AthGeneration,23.6.31,here && export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current &&\
  echo $(date -u +"%Y-%m-%dT%H:%M:%SZ") >> split.log &&\
  Gen_tf.py --ecmEnergy=13000.0 --jobConfig=/atlasgpfs01/usatlas/data/jroblesgo/EVNTJob/centos/EVNTFiles/100xxx/100001/ --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=1001 2>&1 | tee pipe_file.log &&\
  echo $(date -u +"%Y-%m-%dT%H:%M:%SZ") >> split.log"

# Output directory
output_dir="/atlasgpfs01/usatlas/data/jroblesgo/benchmarks/${curr_time}/EVNT_centos7_batch"

# Creates the output directory
mkdir -p "${output_dir}"
# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log
# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Checks the directory, if it matches it cleans it for the next job
if [ "$(pwd)" = "/atlasgpfs01/usatlas/scratch/jroblesgo/EVNT/centos" ]; then
  rm -r ./*
fi
