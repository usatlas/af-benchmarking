#!/bin/bash

curr_time=$(date +"%Y.%m.%dT%H")

# The seed used in the job
seed=1001

# Directory storing the input files
config_dir="/sdf/data/atlas/u/selbor/EVNTJob/container_el/EVNTFiles/100xxx/100001/"


rm -r ./*

cp -r "$HOME"/AF-Benchmarking/EVNT/EVNTFiles .

# Current time used for log file storage
curr_time=$(date +"%Y.%m.%dT%H")

# Appends time before Gen_tf.py to log file
date +"%Y.%m.%d.%H.%M.%S" >> split.log

asetup AthGeneration,23.6.34,here
Gen_tf.py --ecmEnergy=13000.0 --jobConfig=${config_dir} --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed=${seed} 2>&1 | tee pipe_file.log

# Appends time after Gen_tf.py to a log file
date +"%Y.%m.%d.%H.%M.%S" >> split.log

# Defines the output directory
output_dir="/sdf/data/atlas/u/$USER/benchmarks/${curr_time}/EVNT_container_el/"
# Creates the output directory
mkdir -p "${output_dir}"
# Obtains and appends the host name and payload size to the log file
hostname >> split.log
du EVNT.root >> split.log

# Moves the log file and date_name file to the output directory
mv log.generate "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
