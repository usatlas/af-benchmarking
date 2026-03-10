#!/bin/bash
# shellcheck disable=SC1091


# Defines the directory where the input files are stored
config_dir="/data/$USER/TRUTH3_StaticDir/"

# Defines the OS the container will have
OScontainer="el9"

# Sets up the working environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Appends time before Derivation_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c "${OScontainer}" -m /data:/data -r "asetup Athena,24.0.53,here && \
  Derivation_tf.py --CA True --inputEVNTFile ${config_dir}EVNT_el9_interactive.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log"

# Obtains and appends the host machine and payload size to the log file
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  echo "Starting job"
  hostname
  du DAOD_TRUTH3.TRUTH3.root
} >> split.log
