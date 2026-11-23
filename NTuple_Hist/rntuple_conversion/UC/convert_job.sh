#!/bin/bash
# Condor job: convert one TTree ntuple file to RNTuple.
#
# The output keeps the input's file name and goes into a sibling dataset
# directory with "_RNTuple" before the trailing ".root":
#   <dir>/user.X_ANALYSIS.root/f.root -> <dir>/user.X_ANALYSIS_RNTuple.root/f.root
# An existing output is skipped, so resubmitting the whole list is safe.
#
# usage: convert_job.sh <input_file> [output_parent]
# output_parent is the directory in which the "_RNTuple" dataset directory is
# created; it defaults to the input dataset directory's parent. Pass it when
# the input tree is read-only for the submitting user.
#
# No `set -e`/`set -u`: ALRB's setup scripts reference unbound variables.
input="$1"

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -q
# Same LCG view as the event_loop benchmarks; ships ROOT 6.34.
lsetup "views LCG_107a_ATLAS_2 x86_64-el9-gcc13-opt" >/dev/null 2>&1 || {
  echo "lsetup failed" >&2
  exit 2
}
echo "ROOT $(root-config --version) on $(hostname)"

if [[ ! -f "${input}" ]]; then
  echo "input file not found: ${input}" >&2
  exit 2
fi

dataset_dir=$(dirname "${input}")
output_parent="${2:-$(dirname "${dataset_dir}")}"
output_dir="${output_parent}/$(basename "${dataset_dir%.root}")_RNTuple.root"
mkdir -p "${output_dir}"
output="${output_dir}/$(basename "${input}")"

if [[ -e "${output}" ]]; then
  echo "SKIP ${output} already exists"
  exit 0
fi

/usr/bin/time -v python3 convert_ttree_to_rntuple.py "${input}" "${output}"
