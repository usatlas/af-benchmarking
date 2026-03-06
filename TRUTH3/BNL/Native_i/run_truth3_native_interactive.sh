#!/bin/bash

curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 

# Copying input files to working directory
cp -r ~/AF-Benchmarking/TRUTH3/EVNT.root .

# Sets up our environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh

# Sets the Athena version we want
asetup Athena,24.0.53,here

# Appends time before Derivation_tf.py to log file
date +'%H:%M:%S' >> split.log


Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

# Appends time after Derivation_tf.py to a log file
date +'%H:%M:%S' >> split.log

# current time used for log file storage


# Defines the output directory
output_dir="/atlasgpfs01/usatlas/data/jroblesgo/benchmarks/${curr_time}/TRUTH3_native_interactive"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host machine and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# Moves the log file to the output directory
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Checks the directory, if it matches it cleans it for the next job
if [ "$(pwd)" = "/atlasgpfs01/usatlas/scratch/jroblesgo/TRUTH3/native_int" ]; then
  rm -r ./*
fi
