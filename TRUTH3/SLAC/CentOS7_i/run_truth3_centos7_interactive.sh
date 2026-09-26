#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

# Defines the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cd "$HOME"/TRUTH3_int/centos || exit

cp -r "$HOME"/AF-Benchmarking/TRUTH3/EVNT.root .

# Sets up the environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
#
# Because this whole flow runs inside the container's -r string, there's no
# way to capture setup_end or the time -v mode on the host directly -- both
# get written into split.log inside the container and grepped back out
# after the container returns, mirroring
# TRUTH3/BNL/EL9/run_truth3_el9_batch.sh's SETUP_COMPLETE marker.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c centos7 -r "asetup AthDerivation,21.2.178.0,here && \
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log && \
  date -u \"+%Y-%m-%dT%H:%M:%SZ\" >> split.log && \
  if [ -x /usr/bin/time ]; then TIME_CMD='/usr/bin/time -v'; BENCH_MODE=time_v; else TIME_CMD=''; BENCH_MODE=none; fi && \
  echo \"BENCH_MODE=\${BENCH_MODE}\" >> split.log && \
  \${TIME_CMD} Reco_tf.py --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --reductionConf TRUTH3 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.EVNTtoDAOD && \
  date -u \"+%Y-%m-%dT%H:%M:%SZ\" >> split.log"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
bench_mode=$(grep "^BENCH_MODE=" split.log 2>/dev/null | tail -1 | sed 's/^BENCH_MODE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Defines the output directory where the log file will be stored
output_dir="/sdf/data/atlas/u/qlei/benchmarks/${curr_time}/TRUTH3_centos7_int"
# Creates the output directory
mkdir -p "${output_dir}"
# Appends the host-name to the end of the log file
hostname >> split.log
# Appends the size of the output DAOD file to the end of the log file
du DAOD_TRUTH3.TRUTH3.root >> split.log

# This job runs directly on iana (no sbatch/compute node involved), so
# hostname here already reflects where the job actually ran.
hostname > "${output_dir}/hostname.txt"

append_benchmark log.EVNTtoDAOD "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode:-none}"

# Moves the log file to the output directory defined above
mv log.EVNTtoDAOD "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"

# Parse and upload -- this script already runs synchronously to completion
# (no separate sbatch/submit_and_upload.sh needed for the interactive
# variants), so the parse/upload step lives right here.
readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"
export PATH="/sdf/home/q/qlei/.pixi/bin:$PATH"
# shellcheck disable=SC1091
[ -r "$HOME/.secrets" ] && . "$HOME/.secrets"

cd "${AF_BENCH_DIR}" || exit 1

pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
  --job truth3 \
  --log-type truth3 \
  --log-file "${output_dir}/log.EVNTtoDAOD" \
  --cluster "SLAC-AF" \
  --token="${KIBANA_TOKEN}" \
  --kind="benchmark" \
  --host="$(cat "${output_dir}/hostname.txt" 2>/dev/null || hostname)" \
  --os="centos7" \
  --mode="interactive" \
  --containerized="true" \
  --output="${output_dir}/payload.json"

response=$(curl -X POST "${KIBANA_URI}" \
  -H "Content-Type: application/json" \
  -d @"${output_dir}/payload.json" \
  -w "%{http_code}" \
  -s -o "${output_dir}/response.txt")
echo "HTTP Response Code: ${response}"
cat "${output_dir}/response.txt" || true
if [[ ! "${response}" =~ ^2 ]]; then
  echo "Upload failed with HTTP status: ${response}"
  exit 1
fi
echo "Upload successful!"
