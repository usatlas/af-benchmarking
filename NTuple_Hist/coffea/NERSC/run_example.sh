#!/bin/bash

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Run this in a container

cd /pscratch/sd/s/selbor/ntuple/coffea || exit

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase



# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  date >> split.log &&\
  ./venv/bin/python ~/AF-Benchmarking/NTuple_Hist/coffea/NERSC/example.py 2>&1 | tee coffea_hist.log"

{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

log_file_dir="/global/cfs/cdirs/m2616/selbor/benchmarks/${curr_time}/Coffea_Hist/"

mkdir -p "${log_file_dir}"

mv coffea_hist.log "${log_file_dir}"
mv split.log "${log_file_dir}"
