#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the EVNT EL9 batch
# job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="$HOME/AF-Benchmarking"

readonly job_dir="$HOME/EVNTJob/container_el"
readonly sub_file="${AF_BENCH_DIR}/EVNT/SLAC/EL9/evnt_el9_sub.sh"
readonly log_base="/sdf/data/atlas/u/${USER}/benchmarks"
readonly log_output="log.generate"
readonly job_output_name="EVNT_container_el"

readonly pixi_job="evnt"
readonly pixi_log_type="evnt"
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

# The shared wrapper submits, waits, picks this run's output directory and
# uploads it. exec keeps fd 200 open, so the lock is held until it exits.
exec "${AF_BENCH_DIR}/parsing/utils/submit_and_upload.sh" \
  --sub-file "${sub_file}" \
  --output-glob "${log_base}/*/${job_output_name}" \
  --log-name "${log_output}" \
  --cluster "SLAC-AF" \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --os "${pixi_os}" \
  --mode "${pixi_mode}" \
  --containerized "${pixi_containerized}"
