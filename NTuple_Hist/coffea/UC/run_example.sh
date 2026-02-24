#!/bin/bash

date >> split.log

#cp ${GITHUB_WORKSPACE}/NTuple_Hist/coffea/UC/example.py .

# Setting up environment and container
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /data -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  ./venv/bin/python ${GITHUB_WORKSPACE}/NTuple_Hist/coffea/UC/example.py  2>&1 | tee coffea_hist.log"

echo "::group::Collect Metrics"
{
  date +'%H:%M:%S'
  hostname
} >> split.log
echo "::endgroup::"
