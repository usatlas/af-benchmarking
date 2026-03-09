#!/bin/bash

# # Gets the current time

curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cp /sdf/home/s/"$USER"/AF-Benchmarking/NTuple_Hist/coffea/SLAC/example.py .

date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

python3 example.py 2>&1 | tee coffea_hist.log

{
  date -u +"%Y-%m-%dT%H:%M:%SZ"
  hostname
  du coffea.root
} >> split.log

log_file_dir="/sdf/data/atlas/u/selbor/benchmarks/${curr_time}/Coffea_Hist/"

mkdir -p "${log_file_dir}"

mv coffea_hist.log "${log_file_dir}"
mv split.log "${log_file_dir}"
