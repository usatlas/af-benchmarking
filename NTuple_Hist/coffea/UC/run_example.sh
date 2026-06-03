#!/bin/bash

source ./parsing/utils/benchmark_utils.sh

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

#cp ./NTuple_Hist/coffea/UC/example.py .

# Setting up environment and container
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /data -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  /usr/bin/time -v ./venv/bin/python ./NTuple_Hist/coffea/UC/example.py  2>&1 | tee coffea_hist.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
} >> split.log
echo "::endgroup::"

append_benchmark "coffea_hist.log" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
