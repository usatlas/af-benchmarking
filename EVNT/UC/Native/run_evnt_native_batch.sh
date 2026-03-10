#!/bin/bash

# The seed used in the job
seed=1001

# Directory storing the input files
config_dir="${GITHUB_WORKSPACE}/EVNT/EVNTFiles/100xxx/100001"

max_events=1000

# Sets up our working environment
echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"

# Appends time before Gen_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Sets up the Ath* version
asetup AthGeneration,23.6.34,here

echo "::group::EVNT Generation"
Gen_tf.py --ecmEnergy=13000.0 --jobConfig="${config_dir}"  --outputEVNTFile=EVNT.root --maxEvents="${max_events}" --randomSeed="${seed}" 2>&1 | tee pipe_file.log
echo "::endgroup::"

# Appends time after Gen_tf.py to a log file
echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du EVNT.root
} >> split.log
echo "::endgroup::"
