#!/bin/bash

source ./parsing/utils/benchmark_utils.sh

yml_dir=./NTuple_Hist/fastframes/UC/

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up our working environment
echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"

# Set up for FastFrames
asetup StatAnalysis,0.6.3
lsetup emi
printf "%s" "${VOMS_PASSWORD}" | voms-proxy-init -voms atlas
# shellcheck disable=SC1091
source /data/selbor/FastFramesTutorial/TutorialClass/build/setup.sh

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

echo "::group::FastFrames"
/usr/bin/time -v python3 /data/selbor/FastFramesTutorial/FastFrames/python/FastFrames.py -c "${yml_dir}"mc20e_example_config.yml 2>&1 | tee fastframes.log
printf "\n"
echo "::endgroup::"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

# Directory that needs to be cleaned
cleanup_dir="/home/selbor/ntuple/fastframes"

if [[ -d "${cleanup_dir}" && "${cleanup_dir}" == "/home/selbor/ntuple/fastframes" ]]; then
    rm -rf "${cleanup_dir:?}/"*
fi

append_benchmark "fastframes.log" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
