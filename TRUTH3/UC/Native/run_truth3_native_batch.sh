#!/bin/bash
# shellcheck disable=SC1091


# Input files are stored here
config_dir="${GITHUB_WORKSPACE}/TRUTH3/EVNT.root"

# Sets up our environment
echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"

# Appends time before Derivation_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets the Athena version we want
asetup Athena,24.0.53,here

echo "::group::TRUTH3 Derivation"
Derivation_tf.py --CA True --inputEVNTFile "${config_dir}" --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log
echo "::endgroup::"

# Appends time after Derivation_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log


# Obtains and appends the host machine and payload size to the log file
echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  echo "Starting job"
  hostname
  du DAOD_TRUTH3.TRUTH3.root
} >> split.log
echo "::endgroup::"
