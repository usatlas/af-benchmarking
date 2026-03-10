#!/bin/bash

# Gets the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

working_dir="/atlasgpfs01/usatlas/scratch/jroblesgo/ntuple/coffea"

# Goes into the job directory if it exits, creates it otherwise
if [ -d "${working_dir}" ]; then
  cd "${working_dir}" || exit
else
  mkdir -p "${working_dir}"
  cd "${working_dir}" || exit
fi

cp ~/AF-Benchmarking/NTuple_Hist/coffea/BNL/example.py .
cp ~/AF-Benchmarking/NTuple_Hist/coffea/light_roast-0.1.dev10+ge21defc-py3-none-any.whl .

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /atlasgpfs01/usatlas/data/ -r "date >> split.log &&\
  pip3 install  light_roast-0.1.dev10+ge21defc-py3-none-any.whl &&\
  pip3 install atlas_schema &&\
  python3 example.py 2>&1 | tee coffea_hist.log"

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

output_dir="/atlasgpfs01/usatlas/data/jroblesgo/benchmarks/${curr_time}/Coffea_Hist/"

mkdir -p "${output_dir}"

mv coffea_hist.log "${output_dir}"
mv split.log "${output_dir}"
