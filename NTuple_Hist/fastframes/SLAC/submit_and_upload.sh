#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the fastframes
# batch job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"

# The Slurm CWD becomes /srv inside the container (mc20e_example_config.yml
# reads /srv/input_ff/...), so input_ff/ and FastFramesTutorial/ must sit
# directly beneath this directory.
readonly job_dir="/sdf/data/atlas/u/qlei"
readonly sub_file="${AF_BENCH_DIR}/NTuple_Hist/fastframes/SLAC/fastframes_el9_sub.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="fastframes.log"
readonly job_output_name="FastFrames_Hist"

readonly pixi_job="fastframes"
readonly pixi_log_type="fastframes"
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
