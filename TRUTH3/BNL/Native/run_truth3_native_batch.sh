#!/bin/bash

source /usatlas/u/qlei/dev/af-benchmarking/parsing/utils/benchmark_utils.sh

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Copying input files to working directory
cp -r ~/AF-Benchmarking/TRUTH3/EVNT.root .

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up our environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh

# Sets the Athena version we want
asetup Athena,24.0.53,here

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Appends time before Derivation_tf.py to log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

/usr/bin/time -v Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

cat pipe_file.log >> log.Derivation

# Appends time after Derivation_tf.py to a log file
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defines the output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/TRUTH3_native_batch/${start_time}"

# Creates the output directory
mkdir -p "${output_dir}"

# Obtains and appends the host machine and payload size to the log file
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "truth_v"

# Moves the log file to the output directory
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Checks the directory, if it matches it cleans it for the next job
if [ "$(pwd)" = "/usatlas/u/qlei/TRUTH3/el" ]; then
  rm -r ./*
fi
