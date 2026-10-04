#!/bin/bash
# Submits one Slurm benchmark job, waits for it to finish, then parses and
# uploads its log with parse_upload.sh. Meant to run on a login node (e.g.
# from scrontab), so the upload never depends on compute-node network access.
# Site-neutral: every site-specific value arrives as an argument.
#
# Usage: submit_and_upload.sh --sub-file S --output-glob G --log-name L \
#          --cluster C --job J --log-type T --os OS --mode M --containerized B
#
# --output-glob matches the per-run output directories the job writes, e.g.
# "/path/to/benchmarks/*/TRUTH3_el9_container"; quote it
# so the calling shell passes the pattern through. Of the directories created
# after submission, the newest is this run's output.

set -uo pipefail

UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sub_file="" output_glob="" log_name="" cluster="" job="" log_type="" os="" mode="" containerized=""
while [ $# -gt 0 ]; do
  if [ $# -lt 2 ]; then
    echo "ERROR: $1 needs a value" >&2
    exit 2
  fi
  case "$1" in
    --sub-file) sub_file="$2" ;;
    --output-glob) output_glob="$2" ;;
    --log-name) log_name="$2" ;;
    --cluster) cluster="$2" ;;
    --job) job="$2" ;;
    --log-type) log_type="$2" ;;
    --os) os="$2" ;;
    --mode) mode="$2" ;;
    --containerized) containerized="$2" ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift 2
done

for name in sub_file output_glob log_name cluster job log_type os mode containerized; do
  if [ -z "${!name}" ]; then
    echo "ERROR: missing --${name//_/-}" >&2
    exit 2
  fi
done

if [ ! -r "${sub_file}" ]; then
  echo "ERROR: cannot read sub file ${sub_file}" >&2
  exit 2
fi

# Anything newer than this marker was written by the job submitted below. It
# stops a run that crashed before creating its output directory from
# re-uploading the previous run's result.
marker=$(mktemp)
trap 'rm -f "${marker}"' EXIT

# append_benchmark reads SUBMIT_TIME inside the job (sbatch passes the
# submitting environment through by default), which gives the parser a real
# queueTime.
SUBMIT_TIME=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export SUBMIT_TIME

# scrontab sets SLURM_* variables that a child sbatch inherits and can fail
# on (https://docs.nersc.gov/jobs/workflow/scrontab/).
for var in $(compgen -e | grep '^SLURM_'); do
  unset "${var}"
done

echo "Submitting ${sub_file}"
job_id=$(sbatch --wait --parsable "${sub_file}")
sbatch_status=$?
if [ "${sbatch_status}" -ne 0 ]; then
  echo "ERROR: sbatch --wait failed (job ${job_id:-unknown}, exit ${sbatch_status})" >&2
  exit 1
fi
echo "Job ${job_id} completed."

shopt -s nullglob
# shellcheck disable=SC2206 # the pattern must glob-expand here
candidates=(${output_glob})
shopt -u nullglob

new_dirs=()
for dir in "${candidates[@]+"${candidates[@]}"}"; do
  if [ -d "${dir}" ] && [ "${dir}" -nt "${marker}" ]; then
    new_dirs+=("${dir}")
  fi
done
if [ "${#new_dirs[@]}" -eq 0 ]; then
  echo "ERROR: no new output directory matches ${output_glob}" >&2
  exit 1
fi
# shellcheck disable=SC2012 # output dirs are named by UTC timestamps, so ls is safe here
latest_dir=$(ls -dt "${new_dirs[@]}" | head -1)
latest_dir="${latest_dir%/}"
echo "Latest output directory: ${latest_dir}"

"${UTILS_DIR}/parse_upload.sh" \
  --cluster "${cluster}" \
  --job "${job}" \
  --log-type "${log_type}" \
  --log-file "${latest_dir}/${log_name}" \
  --os "${os}" \
  --mode "${mode}" \
  --containerized "${containerized}" \
  --output-dir "${latest_dir}"
