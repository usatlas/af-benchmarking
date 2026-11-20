#!/bin/bash
# shellcheck disable=SC1091

source ./parsing/utils/benchmark_utils.sh

yml_dir=./NTuple_Hist/fastframes/UC/

# Input format: ttree (default) or rntuple. It picks the config, whose only
# difference is the file list, and the log name, so the two formats' benchmarks
# are reported separately.
format="${1:-ttree}"
case "${format}" in
  ttree)
    config=mc20e_example_config.yml
    log_file=fastframes.log
    ;;
  rntuple)
    config=mc20e_example_config_rntuple.yml
    log_file=fastframes_rntuple.log
    ;;
  *)
    echo "unknown format: ${format} (expected ttree or rntuple)" >&2
    exit 2
    ;;
esac

# The FastFrames build is set by the caller (the workflow's env). Both formats
# use the same 7.x build, the first version that reads RNTuple.
: "${FF_DIR:?Set FF_DIR to the directory holding the FastFrames 7.2 build}"

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Sets up our working environment
echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
echo "::endgroup::"

# Set up for FastFrames
asetup StatAnalysis,0.7.3
lsetup emi
printf "%s" "${VOMS_PASSWORD}" | voms-proxy-init -voms atlas
# shellcheck disable=SC1091
source "${FF_DIR}"/TutorialClass/build/setup.sh

setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

echo "::group::FastFrames"
/usr/bin/time -v python3 "${FF_DIR}"/FastFrames/python/FastFrames.py -c "${yml_dir}${config}" 2>&1 | tee "${log_file}"
printf "\n"
echo "::endgroup::"

end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

append_benchmark "${log_file}" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"
