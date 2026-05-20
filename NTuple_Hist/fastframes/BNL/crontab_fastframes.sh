#!/bin/bash

# Configuration
readonly log_base="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple"
readonly log_output="fastframes.log"
readonly job_dir="/usatlas/u/qlei/test/fastframes"
readonly AF_BENCH_DIR="/usatlas/u/qlei/AF-Benchmarking"
readonly sub_file="${AF_BENCH_DIR}/NTuple_Hist/fastframes/BNL/fastframes_el9.sub"

readonly pixi_job="fastframes"
readonly pixi_log_type="fastframes"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="false"

# Environment Setup
export PATH="/usatlas/u/qlei/.pixi/bin:$PATH"

# shellcheck disable=SC1091
[ -r /usatlas/u/qlei/.secrets ] && . /usatlas/u/qlei/.secrets

# Ensure job_dir exists and cd into it before submitting
if [ ! -d "${job_dir}" ]; then
  echo "ERROR: job_dir does not exist: ${job_dir}"
  exit 1
fi

cd "${job_dir}" || { echo "ERROR: Could not cd into ${job_dir}"; exit 1; }
echo "Submitting job from: $(pwd)"

submit_out=$(condor_submit "${sub_file}")
echo "${submit_out}"

# Extract the cluster ID from condor_submit output
cluster_id=$(echo "${submit_out}" | grep -oP '(?<=cluster )\d+')
if [ -z "${cluster_id}" ]; then
  echo "ERROR: Could not determine cluster ID from condor_submit output"
  exit 1
fi
echo "Cluster ID: ${cluster_id}"

# Extract the log path template from the .sub file and expand macros
log_template=$(grep -i '^log' "${sub_file}" | awk '{print $NF}')
condor_log="${log_template//\$(Cluster)/${cluster_id}}"
condor_log="${condor_log//\$(Process)/0}"

echo "Waiting for job to complete (log: ${condor_log})..."
condor_wait "${condor_log}" || { echo "ERROR: condor_wait failed"; exit 1; }
echo "Job completed."

# Get the latest output directory by modification time
latest_dir=$(find "${log_base}" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')

if [ -z "${latest_dir}" ]; then
  echo "ERROR: No directories found in ${log_base}"
  exit 1
fi

echo "Latest output directory: ${latest_dir}"

cd "${AF_BENCH_DIR}" || exit

# Parse the logs and produce the JSON file
pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --log-file "${latest_dir}/${log_output}" \
  --cluster "BNL-AF" \
  --token="${KIBANA_TOKEN}" \
  --kind="benchmark" \
  --host="$(hostname)" \
  --os="${pixi_os}" \
  --mode="${pixi_mode}" \
  --containerized="${pixi_containerized}" \
  --output="${latest_dir}/payload.json"

# Upload the JSON payload to Kibana
response=$(curl -X POST "${KIBANA_URI}" \
  -H "Content-Type: application/json" \
  -d @"${latest_dir}/payload.json" \
  -w "%{http_code}" \
  -s -o "${job_dir}/response.txt")
echo "HTTP Response Code: $response"
echo "Response body:"
cat ${job_dir}/response.txt || true
printf "\n"
if [[ ! "$response" =~ ^2 ]]; then
  echo "Upload failed with HTTP status: $response"
  exit 1
fi
echo "Upload successful!"

find "${job_dir}" -mindepth 1 -delete
