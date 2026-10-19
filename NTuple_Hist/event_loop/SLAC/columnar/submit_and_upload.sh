#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the eventloop
# columnar batch job, blocks until it finishes, then parses and uploads
# the result. Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait
# standing in for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"
# shellcheck disable=SC1091
source "${AF_BENCH_DIR}/parsing/utils/benchmark_utils.sh"

readonly job_dir="/sdf/scratch/atlas/qlei/Ntuple_Hist/event-loop-columnar"
readonly sub_file="${AF_BENCH_DIR}/NTuple_Hist/event_loop/SLAC/columnar/event_loop_arrays.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="event_loop_arrays.log"
readonly job_output_name="eventloop_arrays"

readonly pixi_job="eventloop-columnar"
readonly pixi_log_type="eventloop"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="true"

# Prevent a second cron-triggered run from racing this one: sbatch --wait
# blocks for the job's full walltime, so if a run is still active past the
# next 6-hour cron firing, two overlapping sbatch jobs would both write into
# this shared job_dir at once.
readonly lock_file="${job_dir}.lock"
exec 200>"${lock_file}"
if ! flock -n 200; then
  echo "ERROR: another instance of this job is already running (lock: ${lock_file}) -- exiting without touching ${job_dir}"
  exit 1
fi

# Guarded, unlike the old fire-and-forget wrapper: on a fresh account this
# directory may not exist yet, and a bare cd failing here must not let
# sbatch run from the wrong working directory.
cd "${job_dir}" || { echo "ERROR: could not cd into ${job_dir}"; exit 1; }

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
