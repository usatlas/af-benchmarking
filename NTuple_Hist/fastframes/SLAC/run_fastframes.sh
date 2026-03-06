#!/bin/bash

curr_date=$(date +"%Y.%m.%d.%H.%M.%S") 

asetup StatAnalysis,0.6.2

cd /sdf/data/atlas/u/selbor/FastFramesTutorial/TutorialClass/build || exit

# shellcheck disable=SC1091
source setup.sh

cd - || exit

python3 /srv/FastFramesTutorial/FastFrames/python/FastFrames.py -c /sdf/data/atlas/u/selbor/input_ff/mc20e_example_config.yml 2>&1 | tee fastframes.log

{
  hostname
  du example_FS.root
} >> fastframes.log

file_dir="/sdf/data/atlas/u/selbor/benchmarks/${curr_date}/FastFrames_Hist/"

mkdir -p "${file_dir}"

mv fastframes.log "${file_dir}"
