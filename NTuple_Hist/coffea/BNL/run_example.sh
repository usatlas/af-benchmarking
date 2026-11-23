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
# atlas_schema 0.5.0 gives every photon a default "mass" next to the ntuple's
# own "e" branch, which coffea's Lorentz-vector validation rejects, so it stays
# below 0.5. dask_histogram is listed because coffea 2026.11 no longer pulls it
# in and example.py imports hist.dask.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /atlasgpfs01/usatlas/data/ -r "date >> split.log &&\
  lsetup 'python 3.13.18-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install 'atlas_schema<0.5' 'dask_awkward!=2026.2.0' dask_histogram &&\
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
