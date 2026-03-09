#!/bin/bash

yml_dir="${GITHUB_WORKSPACE}/NTuple_Hist/fastframes/UC/"

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

date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

echo "::group::FastFrames"
python3 /data/selbor/FastFramesTutorial/FastFrames/python/FastFrames.py -c "${yml_dir}"mc20e_example_config.yml 2>&1 | tee fastframes.log
printf "\n"
echo "::endgroup::"

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

# Directory that needs to be cleaned
cleanup_dir="/home/selbor/ntuple/fastframes"

if [[ -d "${cleanup_dir}" && "${cleanup_dir}" == "/home/selbor/ntuple/fastframes" ]]; then
    rm -rf "${cleanup_dir:?}/"*
fi
