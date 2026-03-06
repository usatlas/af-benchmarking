#!/bin/bash
# Current time used for file storage

curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 


# Defines the OS the container will have
OScontainer="el9"
job_dir="$SCRATCH/TRUTH3/el_int/"
mkdir -p "${job_dir}"
cd "${job_dir}" || exit
cp ~/AF-Benchmarking/TRUTH3/EVNT.root .
# Sets up the working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Reco_tf.py to log file
date +'%H:%M:%S' >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c "${OScontainer}" -m /global/cfs/cdirs/m2616/selbor -r "asetup Athena,24.0.53,here && \
  Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log"

# Appends time after Reco_tf.py to a log file
date +'%H:%M:%S' >> split.log

rm EVNT.root

# Defines the output directory
output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/TRUTH3_el9_int"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# Moves the log file to the output directory
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
