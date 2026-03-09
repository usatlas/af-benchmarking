#!/bin/bash
# current time used for log file storage


curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Defines the OS the container will have
OScontainer="centos7"
job_dir="$SCRATCH/TRUTH3/centos7/"
mkdir -p "${job_dir}"
cd "${job_dir}" || exit
cp ~/AF-Benchmarking/TRUTH3/EVNT.root .
# Sets up the working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Reco_tf.py to log file
date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c "${OScontainer}" -m /global/cfs/cdirs/m2616/selbor -r "asetup AthDerivation,21.2.178.0,here && \
  Reco_tf.py --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --reductionConf TRUTH3 2>&1 | tee pipe_file.log"

# Appends time after Reco_tf.py to a log file
date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

rm EVNT.root

# Defining the output directory
output_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/TRUTH3_centos/"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# Moves the log file to the output directory
mv log.EVNTtoDAOD "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

rm ./*
