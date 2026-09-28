#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the TRUTH3 CentOS7
# batch job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"
readonly job_dir="/sdf/home/q/qlei/TRUTH3Job/container_centos"
readonly sub_file="${AF_BENCH_DIR}/TRUTH3/SLAC/CentOS7/truth3_centos7_sub.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="log.EVNTtoDAOD"
readonly job_output_name="TRUTH3_centos7_container"

readonly pixi_job="truth3"
readonly pixi_log_type="truth3"
readonly pixi_os="centos7"
readonly pixi_mode="batch"
readonly pixi_containerized="true"

export PATH="/sdf/home/q/qlei/.pixi/bin:$PATH"
# shellcheck disable=SC1091
[ -r "$HOME/.secrets" ] && . "$HOME/.secrets"

# Prevent a second cron-triggered run from racing this one: sbatch --wait
# blocks for the job's full walltime, so if a run is still active past the
# next 6-hour cron firing, an unguarded rm -rf below would delete the
# still-running job's working directory out from under it.
readonly lock_file="${job_dir}.lock"
exec 200>"${lock_file}"
if ! flock -n 200; then
  echo "ERROR: another instance of this job is already running (lock: ${lock_file}) -- exiting without touching ${job_dir}"
  exit 1
fi

cd "${job_dir}" || { echo "ERROR: could not cd into ${job_dir}"; exit 1; }
rm -rf ./*

echo "Submitting ${sub_file}"
job_id=$(sbatch --wait --parsable "${sub_file}")
sbatch_status=$?
if [ "${sbatch_status}" -ne 0 ]; then
  echo "ERROR: sbatch --wait failed (job ${job_id:-unknown}, exit ${sbatch_status})"
  exit 1
fi
echo "Job ${job_id} completed."

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

# Without this, a failed/crashed ci_parse leaves no payload.json, and curl
# below would silently POST an empty body that still returns HTTP 200 -- a
# false "Upload successful!" with nothing actually in Kibana.
if [ ! -s "${latest_dir}/payload.json" ]; then
  echo "ERROR: ci_parse did not produce a payload -- see output above"
  exit 1
fi

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
