#!/bin/bash

# shellcheck disable=SC1091
source ./parsing/utils/benchmark_utils.sh

# Input format: ttree (default) or rntuple. The config's only difference is the
# file list. The TTree job runs in the qlei directory, whose input/ is kept by
# hand; the RNTuple job gets its own directory, filled from the repo on every
# run, so the two never share logs, split.log or the output histogram.
format="${1:-ttree}"
case "${format}" in
  ttree)
    variant_suffix=""
    working_dir=/atlasgpfs01/usatlas/data/qlei
    config=mc20e_example_config.yml
    ;;
  rntuple)
    variant_suffix="_rntuple"
    working_dir=/atlasgpfs01/usatlas/data/qlei/fastframes_rntuple
    config=mc20e_example_config_rntuple.yml
    mkdir -p "${working_dir}/input" "${working_dir}/output"
    cp ~/AF-Benchmarking/NTuple_Hist/fastframes/BNL/{mc20e_example_config_rntuple.yml,mc20e_filelist_rntuple.txt,mc20e_sumweights.txt} "${working_dir}/input/"
    ;;
  *)
    echo "unknown format: ${format} (expected ttree or rntuple)" >&2
    exit 2
    ;;
esac
log_file="fastframes${variant_suffix}.log"

# current time used for log file storage
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

cd "${working_dir}" || exit

# Sets up ATLAS environment
echo "::group::setupATLAS"
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
echo "::endgroup::"

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -m /atlasgpfs01/usatlas/data/ -c el9 -r "asetup StatAnalysis,0.7.3 &&\
  source /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3/TutorialClass/build/setup.sh &&\
  echo \"SETUP_COMPLETE=\$(date -u '+%Y-%m-%dT%H:%M:%SZ')\" >> split.log &&\
  /usr/bin/time -v python3 /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3/FastFrames/python/FastFrames.py -c ${working_dir}/input/${config} 2>&1 | tee ${log_file}"

# Getting the date and time after running script
echo "::group::Collect Metrics"
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

# Getting the host-machine's name
hostname >> split.log
echo "::endgroup::"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# output directory
output_dir="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple${variant_suffix}/${start_time}"

# Creates output dir
mkdir -p "${output_dir}"

append_benchmark "${log_file}" "${start_time}" "${end_time}" "${setup_start}" "${setup_end}"

# Moves log to outputdir
mv "${log_file}" "${output_dir}"
mv split.log "${output_dir}"
