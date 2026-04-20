#!/bin/bash

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cd /atlasgpfs01/usatlas/data/qlei/ || exit

# Sets up ATLAS environment
echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
echo "::endgroup::"

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -m /atlasgpfs01/usatlas/data/ -c el9 -r "asetup StatAnalysis,0.6.2 &&\
  source /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial/TutorialClass/build/setup.sh &&\
  python3 /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial/FastFrames/python/FastFrames.py -c /atlasgpfs01/usatlas/data/qlei/input/mc20e_example_config.yml 2>&1 | tee fastframes.log"

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

# output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple/${curr_time}"

# Creates output dir
mkdir -p "${output_dir}"

# Moves log to outputdir
mv fastframes.log "${output_dir}"
