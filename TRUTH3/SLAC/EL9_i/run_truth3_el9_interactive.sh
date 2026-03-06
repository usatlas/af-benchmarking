#!/bin/bash

# Defines the current time
curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 


cd "$HOME"/TRUTH3_int/el || exit

cp -r "$HOME"/AF-Benchmarking/TRUTH3/EVNT.root .

# Sets up the environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase


# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -r "asetup Athena,24.0.53,here && \
  date +'%H:%M:%S' >> split.log && \
  Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log && \
  date +'%H:%M:%S' >> split.log"


# Defines the output directory where the log file will be stored
output_dir="/sdf/data/atlas/u/selbor/benchmarks/${curr_time}/TRUTH3_el9_int"

# Creates the output directory
mkdir -p "${output_dir}"
# Appends the host-name to the end of the log file
hostname >> split.log
# Appends the size of the output DAOD file to the end of the log file
du DAOD_TRUTH3.TRUTH3.root >> split.log
# Moves the log file to the output directory defined above
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
