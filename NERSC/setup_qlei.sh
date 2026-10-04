#!/bin/bash
# One-time setup of the qlei account on Perlmutter for the NERSC benchmarks.
# Creates the directories the jobs cd into and write to, stages the job
# inputs that live in this repo, and downloads the ntuple dataset with Rucio.
# Safe to re-run: existing EVNT job-option copies are kept, repo inputs are
# refreshed, and rucio download skips files it already has.
#
# What it cannot do is printed at the end (credentials, FastFrames build).

set -uo pipefail

AF_BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Overridable only so the tests can point these at a sandbox.
CFS_DIR="${CFS_DIR:-/global/cfs/cdirs/m2616/qlei}"
ATLAS_LOCAL_ROOT_BASE="${ATLAS_LOCAL_ROOT_BASE:-/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase}"
export ATLAS_LOCAL_ROOT_BASE
readonly DATASET="user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root"
readonly DATASET_SCOPE="user.bhodkins"
# The Rucio job mounts ${CFS_DIR}/benchmarks at /srv and reads /srv/pass.txt,
# so this one file serves both that job and the download below.
readonly PASS_FILE="${CFS_DIR}/benchmarks/pass.txt"

if [ -z "${SCRATCH:-}" ]; then
  echo "ERROR: SCRATCH is not set (Perlmutter sets it at login)" >&2
  exit 1
fi

echo "== Directories"
mkdir -p "${CFS_DIR}/benchmarks" \
  "${CFS_DIR}/wrapper_logs" \
  "${CFS_DIR}/fastframes_input" \
  "${HOME}/af_benchmarking/rucio" \
  "${SCRATCH}/TRUTH3/el9" \
  "${SCRATCH}/TRUTH3/centos7" \
  "${SCRATCH}/EVNT/el9" \
  "${SCRATCH}/EVNT/centos7" \
  "${SCRATCH}/ntuple/coffea/single_campaign_mc20e_dataset_runnable" \
  "${SCRATCH}/ntuple/eventloop_arrays" \
  "${SCRATCH}/ntuple/eventloop_noarrays" || exit 1

echo "== EVNT job options"
# The EVNT jobs copy ~/evnt_<os>/ and read evnt_<os>/100xxx/100001.
for name in evnt_el9 evnt_centos7; do
  if [ -d "${HOME}/${name}" ]; then
    echo "keep existing ${HOME}/${name}"
  else
    cp -r "${AF_BENCH_DIR}/EVNT/EVNTFiles" "${HOME}/${name}" || exit 1
  fi
done

echo "== coffea and FastFrames inputs"
# $SCRATCH is purged after weeks of inactivity, so this copy is refreshed on
# every run rather than kept.
cp "${AF_BENCH_DIR}/NTuple_Hist/coffea/NERSC/single_campaign_mc20e_dataset_runnable/af_v2_700402.json" \
  "${SCRATCH}/ntuple/coffea/single_campaign_mc20e_dataset_runnable/" || exit 1
# The FastFrames job mounts ${CFS_DIR} at /srv and reads /srv/fastframes_input.
for name in mc20e_example_config.yml mc20e_filelist.txt mc20e_sumweights.txt; do
  cp "${AF_BENCH_DIR}/NTuple_Hist/fastframes/NERSC/${name}" "${CFS_DIR}/fastframes_input/" || exit 1
done

echo "== ntuple dataset"
download_status=0
if [ ! -r "${PASS_FILE}" ]; then
  echo "SKIP: ${PASS_FILE} not found -- create it (see below) and re-run to download ${DATASET}"
else
  # Same ALRB config as the Rucio job (Rucio/rucio_script.sh).
  export ALRB_localConfigDir="${HOME}/localConfig"
  # ALRB is not nounset-safe, so keep set -u out of it.
  set +u
  # shellcheck disable=SC1091
  source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global:/global -r "export RUCIO_ACCOUNT=qlei && \
    lsetup rucio && \
    cat ${PASS_FILE} | voms-proxy-init -voms atlas && \
    rucio download --dir ${CFS_DIR} ${DATASET_SCOPE}:${DATASET}"
  download_status=$?
  set -u
  if [ "${download_status}" -ne 0 ]; then
    echo "ERROR: dataset download failed (exit ${download_status})" >&2
  fi
fi

cat <<EOF

== Manual steps this script does not do
 - ${PASS_FILE}: your grid certificate passphrase, chmod 600 (CFS is group-readable by m2616).
 - FastFramesTutorial built at ${CFS_DIR}/FastFramesTutorial (the job sources TutorialClass/build/setup.sh).
 - ~/localConfig for ALRB (FastFrames and Rucio set ALRB_localConfigDir to it).
 - ~/.secrets exporting KIBANA_TOKEN and KIBANA_URI, and pixi installed in ~/.pixi.
EOF

exit "${download_status}"
