#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the TRUTH3 EL9
# batch job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"
# shellcheck disable=SC1091
source "${AF_BENCH_DIR}/parsing/utils/benchmark_utils.sh"

readonly job_dir="/sdf/home/q/qlei/TRUTH3Job/container_el"
readonly sub_file="${AF_BENCH_DIR}/TRUTH3/SLAC/EL9/truth3_el9_sub.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="log.Derivation"
readonly job_output_name="TRUTH3_el9_container"

readonly pixi_job="truth3"
readonly pixi_log_type="truth3"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="true"

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

# Clean the job's scratch directory before submitting, same as the old
# fire-and-forget wrapper did.
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

latest_dir=$(find_latest_output_dir "${log_base}" "${job_output_name}")

"${AF_BENCH_DIR}/parsing/utils/parse_upload.sh" \
  --cluster "SLAC-AF" \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --log-file "${latest_dir}/${log_output}" \
  --os "${pixi_os}" \
  --mode "${pixi_mode}" \
  --containerized "${pixi_containerized}" \
  --output-dir "${latest_dir}"
