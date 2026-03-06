#!/bin/bash

asetup StatAnalysis,0.6.2

# Time that will be used to store the log file
curr_time=$(date +"%Y.%m.%d.%H.%M.%S") 

date +"%Y.%m.%d.%H.%M.%S" >> split.log

cp /sdf/home/s/"$USER"/AF-Benchmarking/NTuple_Hist/event_loop/SLAC/standard/event_loop_noarrays.py .

python3 event_loop_noarrays.py 2>&1 | tee event_loop_noarrays.log

# Getting end date
date +"%Y.%m.%d.%H.%M.%S" >> split.log

# Getting host name
{
  hostname
  du event_loop_output_hist.root
} >> split.log

output_dir="/sdf/data/atlas/u/selbor/benchmarks/${curr_time}/eventloop_noarrays/"

mkdir -p "${output_dir}"

mv event_loop_noarrays.log "${output_dir}"
mv split.log "${output_dir}"
