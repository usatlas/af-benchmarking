#!/bin/bash

source "${GITHUB_WORKSPACE}/parsing/utils/benchmark_utils.sh"

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_epoch=$(date -u +%s)

#cp ${GITHUB_WORKSPACE}/NTuple_Hist/coffea/UC/example.py .

# Setting up environment and container
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /data -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  /usr/bin/time -v ./venv/bin/python ${GITHUB_WORKSPACE}/NTuple_Hist/coffea/UC/example.py  2>&1 | tee coffea_hist.log"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
end_epoch=$(date -u +%s)
wall_time=$((end_epoch - start_epoch))

echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
} >> split.log
echo "::endgroup::"

append_benchmark "coffea_hist.log" "${start_time}" "${wall_time}" "${end_time}" "time_v"
