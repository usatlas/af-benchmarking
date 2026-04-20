#!/bin/bash

# Gets the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

working_dir="/atlasgpfs01/usatlas/data/qlei/ntuple/coffea"

echo $(pwd)

# Goes into the job directory if it exits, creates it otherwise
if [ -d "${working_dir}" ]; then
  cd "${working_dir}" || exit
else
  mkdir -p "${working_dir}"
  cd "${working_dir}" || exit
fi

echo $(pwd)

cp ~/AF-Benchmarking/NTuple_Hist/coffea/BNL/example.py .

# Check available space and quota
echo "=== Disk usage ==="
df -h "${working_dir}"
du -sh "${working_dir}"

echo "=== Quota ==="
quota -s 2>/dev/null || echo "quota command unavailable"

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /atlasgpfs01/usatlas/data/ -r "date >> split.log &&\
  python3 -m venv venv &&\
  echo \$(pwd) &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  echo \$(pwd) &&\
  ./venv/bin/python example.py 2>&1 | tee coffea_hist.log"
 
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

output_dir="/atlasgpfs01/usatlas/data/qlei/logs/Coffea_Hist/${curr_time}"

mkdir -p "${output_dir}"

mv coffea_hist.log "${output_dir}"
mv split.log "${output_dir}"
