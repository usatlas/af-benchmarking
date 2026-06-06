#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# current time used for log file storage

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

working_dir="/atlasgpfs01/usatlas/data/qlei/ntuple/coffea"

# Goes into the job directory if it exits, creates it otherwise
if [ -d "${working_dir}" ]; then
  cd "${working_dir}" || exit
else
  mkdir -p "${working_dir}"
  cd "${working_dir}" || exit
fi

cp ~/AF-Benchmarking/NTuple_Hist/coffea/BNL/example.py .

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /atlasgpfs01/usatlas/data/ -r "date >> split.log &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  /usr/bin/time -v ./venv/bin/python example.py 2>&1 | tee coffea_hist.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

output_dir="/atlasgpfs01/usatlas/data/qlei/logs/Coffea_Hist/${start_time}"

mkdir -p "${output_dir}"

append_benchmark coffea_hist.log "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"

mv coffea_hist.log "${output_dir}"
mv split.log "${output_dir}"
