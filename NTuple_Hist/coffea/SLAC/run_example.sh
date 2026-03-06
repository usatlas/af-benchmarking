#!/bin/bash

# # Gets the current time

curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 

cp /sdf/home/s/"$USER"/AF-Benchmarking/NTuple_Hist/coffea/SLAC/example.py .

date +"%Y.%m.%d.%H.%M.%S" >> split.log

python3 example.py 2>&1 | tee coffea_hist.log

{
  date +"%Y.%m.%d.%H.%M.%S"
  hostname
  du coffea.root
} >> split.log

log_file_dir="/sdf/data/atlas/u/selbor/benchmarks/${curr_time}/Coffea_Hist/"

mkdir -p "${log_file_dir}"

mv coffea_hist.log "${log_file_dir}"
mv split.log "${log_file_dir}"
