#!/bin/bash
# shellcheck disable=SC1091

source ./parsing/utils/benchmark_utils.sh

# The ntuples are staged by the caller since their location differs per site
: "${NTUPLE_DIR:?Set NTUPLE_DIR to the directory holding the mc20e ntuples}"

# Input format: ttree (default) or rntuple. It picks the dataset copy and the
# log name, so the two formats' benchmarks are reported separately.
format="${1:-ttree}"
case "${format}" in
  ttree) log_file=coffea_hist.log ;;
  rntuple)
    log_file=coffea_hist_rntuple.log
    # The RNTuple copy sits next to the TTree one; see
    # docs/uchicago/rntuple-conversion.md
    NTUPLE_DIR="${NTUPLE_DIR%.root}_RNTuple.root"
    ;;
  *)
    echo "unknown format: ${format} (expected ttree or rntuple)" >&2
    exit 2
    ;;
esac

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

#cp ./NTuple_Hist/coffea/UC/example.py .

# Setting up environment and container
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m "${NTUPLE_DIR}" -r "lsetup 'python 3.9.22-x86_64-el9' &&\
  python3 -m venv venv &&\
  ./venv/bin/python -m pip install -U pip &&\
  ./venv/bin/python -m pip install atlas_schema 'dask_awkward!=2026.2.0' &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  export NTUPLE_DIR='${NTUPLE_DIR}' &&\
  /usr/bin/time -v ./venv/bin/python ./NTuple_Hist/coffea/UC-ODF/example.py --format ${format} 2>&1 | tee ${log_file}"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

echo "::group::Collect Metrics"
{
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  hostname
} >> split.log
echo "::endgroup::"

append_benchmark "${log_file}" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
