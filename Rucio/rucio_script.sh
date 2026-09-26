#! /usr/bin/env bash

# Resolved relative to this script rather than hardcoded per-site, so it
# works no matter which site or account this repo is checked out under.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
AF_BENCH_DIR="${SCRIPT_DIR}/.."
# shellcheck disable=SC1091
source "${AF_BENCH_DIR}/parsing/utils/benchmark_utils.sh"

# Gets the current time
curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

download_ID="archive:mc23_13p6TeV.700866.Sh_2214_WWW_3l3v_EW6.deriv.DAOD_PHYSLITE.e8532_e8528_s4162_s4114_r14622_r14663_p6491_tid41635253_00"

container_el9 (){
  # Takes the following parameters:
  # - job_dir (1)
  # - dir_mount (2)
  # - output_dir (3)
  # - download_ID (4)
  start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
  cd "${1}" || exit
  export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
  export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
# shellcheck disable=SC2115
  source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m "${2}" -r "export RUCIO_ACCOUNT=qlei && \
    lsetup rucio &&\
    cat /srv/pass.txt | voms-proxy-init -voms atlas && \
    mkdir -p \"${3}\" &&\
    [ -d \"${4#*:}\" ] && rm -rf \"${4#*:}\" || true &&\
    rucio download --rses AGLT2_LOCALGROUPDISK \"${4}\"  2>&1 | tee rucio.log &&\
    hostname >> rucio.log &&\
    du \"${4#*:}\"/ >> rucio.log &&\
    mv rucio.log \"${3}\""
  end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
  append_benchmark "${3}/rucio.log" "${start_time}" "${end_time}" "${start_time}" "${start_time}" "rucio"
}

native_el9 () {
  # Takes the following parameters:
  # - output_dir
  # - job_dir
  # - download_ID
  start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
  echo "::group::setupATLAS"
  export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
  export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
  source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh
  echo "::endgroup::"
  lsetup emi "rucio -w"
  printf "%s" "${VOMS_PASSWORD}" | voms-proxy-init -voms atlas
  mkdir -p "${1}"
  cd "${2}" || exit
  tmp="${3:?}"
  # shellcheck disable=SC2115
  rm -r "${tmp#*:}"
  echo "::group::Rucio Download"
  rucio download --rses AGLT2_LOCALGROUPDISK "${3}"  2>&1 | tee rucio.log
  echo "::endgroup::"
  end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
  echo "::group::Collect Metrics"
  hostname >> rucio.log
  du "${3#*:}" >> rucio.log
  echo "::endgroup::"
  append_benchmark "rucio.log" "${start_time}" "${end_time}" "${start_time}" "${start_time}" "rucio"
  mv rucio.log "${1}"
}

# --- Determine site ---
# Conditional block determines the AF
# If the directory exists run the commands in the block
site="$1"
if [[ -z "$site" ]]; then
    # Auto-detect
    if [[ -d /sdf ]]; then
        site="slac"
    elif [[ -d /usatlas ]]; then
        site="uchicago"
    elif [[ -d /data ]]; then
        site="bnl"
    elif [[ -d /pscratch ]]; then
        site="nersc"
    else
        echo "Cannot detect site from directories"
        exit 1
    fi
fi
echo "Running for site: $site"

# --- Configure directories based on site ---
case "$site" in
    bnl)
        job_dir="/usatlas/u/qlei/test/Rucio/"
        dir_mount="/atlasgpfs01/usatlas/data/"
        output_dir="/atlasgpfs01/usatlas/data/qlei/logs/Rucio/${curr_time}/"
        container_el9 "$job_dir" "$dir_mount" "$output_dir" "$download_ID"
        ;;
    slac)
        job_dir="$HOME/af_benchmarking/rucio/"
        dir_mount="/sdf/data/atlas/u/qlei/benchmarks/"
        output_dir="${job_dir}/logs/${curr_time}/"
        container_el9 "$job_dir" "$dir_mount" "$output_dir" "$download_ID"

        # Unlike the other SLAC jobs, this one runs directly on iana (no
        # sbatch/compute node involved) via container_el9's synchronous -r
        # launch, so $(hostname) below already reflects where it ran --
        # no hostname.txt indirection needed. Parse+upload only ever ran
        # here for SLAC before via the now-retired external
        # parsing_jobs/cron_parsing.sh; wire it in directly instead.
        export PATH="$HOME/.pixi/bin:$PATH"
        # shellcheck disable=SC1091
        [ -r "$HOME/.secrets" ] && . "$HOME/.secrets"

        # ci_parse imports the repo's own `parsing` package via `-m`, which
        # resolves relative to CWD -- and container_el9 above already cd'd
        # into job_dir, not the repo root. Without this, ci_parse fails with
        # ModuleNotFoundError and payload.json is never written.
        cd "${AF_BENCH_DIR}" || exit 1

        pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
          --job rucio \
          --log-type rucio \
          --log-file "${output_dir}/rucio.log" \
          --cluster "SLAC-AF" \
          --token="${KIBANA_TOKEN}" \
          --kind="benchmark" \
          --host="$(hostname)" \
          --os="alma9" \
          --mode="batch" \
          --containerized="true" \
          --output="${output_dir}/payload.json"

        # Without this, a failed/crashed ci_parse leaves no payload.json,
        # and curl below would silently POST an empty body that still
        # returns HTTP 200 -- a false "Upload successful!" with nothing
        # actually in Kibana. `-s` here is "file exists and is non-empty".
        if [ ! -s "${output_dir}/payload.json" ]; then
          echo "ERROR: ci_parse did not produce a payload -- see output above"
          exit 1
        fi

        response=$(curl -X POST "${KIBANA_URI}" \
          -H "Content-Type: application/json" \
          -d @"${output_dir}/payload.json" \
          -w "%{http_code}" \
          -s -o "${output_dir}/response.txt")
        echo "HTTP Response Code: ${response}"
        cat "${output_dir}/response.txt" || true
        if [[ ! "${response}" =~ ^2 ]]; then
          echo "Upload failed with HTTP status: ${response}"
          exit 1
        fi
        echo "Upload successful!"
        ;;
    uchicago)
        output_dir="${PWD}"
        native_el9 "${PWD}" "${PWD}" "$download_ID"
        ;;
    nersc)
        job_dir="$HOME/af_benchmarking/rucio/"
        dir_mount="/global/cfs/cdirs/m2616/selbor/benchmarks/"
        output_dir="${job_dir}/logs/${curr_time}/"
        container_el9 "${job_dir}" "${dir_mount}" "${output_dir}" "${download_ID}"
        ;;
    *)
        echo "Unknown site: $site"
        exit 1
        ;;
esac

echo "Download complete. Output dir: $output_dir"
