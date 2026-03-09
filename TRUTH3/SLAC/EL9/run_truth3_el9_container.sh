#!/bin/bash

# Defines the current time
curr_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")


# Appends time before Derivation_tf.py to log file
date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

asetup Athena,24.0.53,here
Derivation_tf.py --CA True --inputEVNTFile /sdf/data/atlas/u/selbor/TRUTH3Files/el/EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

# Appends time after Derivation_tf.py to a log file
date -u +"%Y-%m-%dT%H:%M:%SZ" >> split.log

# Defines the output directory where the log file will be stored
output_dir="/sdf/data/atlas/u/$USER/benchmarks/${curr_time}/TRUTH3_el9_container"

# Creates the output directory
mkdir -p "${output_dir}"
# Appends the host-name to the end of the log file
hostname >> split.log
# Appends the size of the output DAOD file to the end of the log file
du DAOD_TRUTH3.TRUTH3.root >> split.log
# Moves the log file to the output directory defined above
mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
