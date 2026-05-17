#!/bin/bash

source "${GITHUB_WORKSPACE}/parsing/utils/benchmark_utils.sh"

# The seed used in the job
seed=1001

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Directory storing the input files
config_dir="${GITHUB_WORKSPACE}/EVNT/EVNTFiles/100xxx/100001"

max_events=1000

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

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

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

echo "::group::EVNT Generation"
/usr/bin/time -v Gen_tf.py --ecmEnergy=13000.0 --jobConfig="${config_dir}"  --outputEVNTFile=EVNT.root --maxEvents="${max_events}" --randomSeed="${seed}" 2>&1 | tee pipe_file.log
cat pipe_file.log >> log.generate
echo "::endgroup::"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time after Gen_tf.py to a log file
echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du EVNT.root
} >> split.log
echo "::endgroup::"

append_benchmark "log.generate" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
