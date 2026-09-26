#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the coffea batch
# job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"
readonly job_dir="/sdf/scratch/atlas/qlei/Ntuple_Hist/coffea"
readonly sub_file="${AF_BENCH_DIR}/NTuple_Hist/coffea/SLAC/coffea_el9_sub.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="coffea_hist.log"
readonly job_output_name="Coffea_Hist"

readonly pixi_job="coffea"
readonly pixi_log_type="coffea"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="true"

# cron has no PATH and no login shell; mirrors cron_el_batch.sh:17,20
export PATH="/sdf/home/q/qlei/.pixi/bin:$PATH"
# shellcheck disable=SC1091
[ -r "$HOME/.secrets" ] && . "$HOME/.secrets"

# Guarded, unlike the old fire-and-forget wrapper: on a fresh account this
# directory may not exist yet, and a bare cd failing here must not let
# sbatch run (and any later cleanup) from the wrong working directory.
cd "${job_dir}" || { echo "ERROR: could not cd into ${job_dir}"; exit 1; }

echo "Submitting ${sub_file}"
job_id=$(sbatch --wait --parsable "${sub_file}")
sbatch_status=$?
if [ "${sbatch_status}" -ne 0 ]; then
  echo "ERROR: sbatch --wait failed (job ${job_id:-unknown}, exit ${sbatch_status})"
  exit 1
fi
echo "Job ${job_id} completed."

# Find the output directory the payload script just wrote, by mtime
# (mirrors cron_el_batch.sh:52, adapted: Slurm gives us no direct
# equivalent of HTCondor's per-cluster log path).
latest_dir=$(find "${log_base}" -mindepth 2 -maxdepth 2 -type d -name "${job_output_name}" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')
if [ -z "${latest_dir}" ]; then
  echo "ERROR: no ${job_output_name} directory found under ${log_base}"
  exit 1
fi
echo "Latest output directory: ${latest_dir}"

cd "${AF_BENCH_DIR}" || exit 1

pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --log-file "${latest_dir}/${log_output}" \
  --cluster "SLAC-AF" \
  --token="${KIBANA_TOKEN}" \
  --kind="benchmark" \
  --host="$(cat "${latest_dir}/hostname.txt" 2>/dev/null || hostname)" \
  --os="${pixi_os}" \
  --mode="${pixi_mode}" \
  --containerized="${pixi_containerized}" \
  --output="${latest_dir}/payload.json"

response=$(curl -X POST "${KIBANA_URI}" \
  -H "Content-Type: application/json" \
  -d @"${latest_dir}/payload.json" \
  -w "%{http_code}" \
  -s -o "${latest_dir}/response.txt")
echo "HTTP Response Code: ${response}"
cat "${latest_dir}/response.txt" || true
if [[ ! "${response}" =~ ^2 ]]; then
  echo "Upload failed with HTTP status: ${response}"
  exit 1
fi
echo "Upload successful!"
