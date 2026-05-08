#!/bin/bash
# shellcheck disable=SC1091

source "${GITHUB_WORKSPACE}/parsing/utils/benchmark_utils.sh"

# Defines the directory where the input files are stored
config_dir="${GITHUB_WORKSPACE}/TRUTH3/EVNT.root"

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up the environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Derivation_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -r "asetup Athena,24.0.53,here && \
  /usr/bin/time -v Derivation_tf.py --CA True --inputEVNTFile ${config_dir} --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.Derivation"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Obtains and appends the host machine and payload size to the log file
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  echo "Starting job"
  hostname
  du DAOD_TRUTH3.TRUTH3.root
} >> split.log

append_benchmark "log.Derivation" "${start_time}" "${end_time}" "time_v"
