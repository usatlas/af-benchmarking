#!/bin/bash

curr_date=$(date +"%Y.%m.%d.%H.%M.%S") 

cd /atlasgpfs01/usatlas/data/jroblesgo/ || exit

# Sets up ATLAS environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -m /atlasgpfs01/usatlas/data/ -c el9 -r "asetup StatAnalysis,0.6.2 &&\
  source /srv/FastFramesTutorial/TutorialClass/build/setup.sh &&\
  python3 /srv/FastFramesTutorial/FastFrames/python/FastFrames.py -c /srv/input/mc20e_example_config.yml 2>&1 | tee fastframes.log"

{
  hostname
  du example_FS
} >> fastframes.log


# output directory
output_dir="/atlasgpfs01/usatlas/data/jroblesgo/benchmarks/$curr_date/FastFrames_NTuple"

# Creates output dir
mkdir -p "${output_dir}"

# Moves log to outputdir
mv fastframes.log "${output_dir}"
