#!/bin/bash

# Current time used for log file storage
curr_time=$(date +"%Y.%m.%dT%H")

OS_container="centos7"

# The seed used in the job
seed=1001

# Directory storing the input files
config_dir="evnt_centos7/100xxx/100001"
cd "$SCRATCH"/EVNT/centos7/ || exit
cp -r "$HOME"/evnt_centos7/ .
# Creates the ATLAS Environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

date +"%Y.%m.%d.%H.%M.%S" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c ${OS_container} -m /global/cfs/cdirs/m2616/selbor -r "asetup AthGeneration,23.6.31,here && export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current && Gen_tf.py --ecmEnergy=13000.0 --jobConfig=${config_dir} --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=${seed} 2>&1 | tee pipe_file.log"

date +"%Y.%m.%d.%H.%M.%S" >> split.log

rm -r evnt_centos7/

# Defines and makes the output directory
output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/EVNT_centos7/"
mkdir -p "${output_dir}"

# Appends the hostname and payload size to the log files
hostname >> split.log
du EVNT.root >> split.log

# Moves the log file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
