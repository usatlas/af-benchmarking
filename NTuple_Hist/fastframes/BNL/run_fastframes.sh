#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cd /atlasgpfs01/usatlas/data/qlei/ || exit

# Sets up ATLAS environment
echo "::group::setupATLAS"
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
echo "::endgroup::"

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -m /atlasgpfs01/usatlas/data/ -c el9 -r "asetup StatAnalysis,0.6.3 &&\
  source /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial/TutorialClass/build/setup.sh &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  /usr/bin/time -v python3 /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial/FastFrames/python/FastFrames.py -c /atlasgpfs01/usatlas/data/qlei/input/mc20e_example_config.yml 2>&1 | tee fastframes.log"

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple/${start_time}"

# Creates output dir
mkdir -p "${output_dir}"

append_benchmark fastframes.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"

# Moves log to outputdir
mv fastframes.log "${output_dir}"
mv split.log "${output_dir}"

