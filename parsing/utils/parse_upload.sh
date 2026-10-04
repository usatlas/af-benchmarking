#!/bin/bash
# Parses one benchmark log with ci_parse and POSTs the payload to LogStash.
# Site-neutral: every site-specific value arrives as an argument.
#
# Usage: parse_upload.sh --cluster C --job J --log-type T --log-file F \
#          --os OS --mode M --containerized true|false --output-dir D
#
# --log-file and --output-dir must be absolute (this script cd's to the repo
# root so ci_parse can be run as a module). KIBANA_TOKEN and KIBANA_URI come
# from ~/.secrets. The host reported to Kibana is read from
# <output-dir>/hostname.txt, written by the job on the node that ran it,
# because this script runs on a login node.

set -uo pipefail

# The payload carries the Kibana token and CFS output dirs are group-readable.
umask 077

AF_BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cluster="" job="" log_type="" log_file="" os="" mode="" containerized="" output_dir=""
while [ $# -gt 0 ]; do
  if [ $# -lt 2 ]; then
    echo "ERROR: $1 needs a value" >&2
    exit 2
  fi
  case "$1" in
    --cluster) cluster="$2" ;;
    --job) job="$2" ;;
    --log-type) log_type="$2" ;;
    --log-file) log_file="$2" ;;
    --os) os="$2" ;;
    --mode) mode="$2" ;;
    --containerized) containerized="$2" ;;
    --output-dir) output_dir="$2" ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift 2
done

for name in cluster job log_type log_file os mode containerized output_dir; do
  if [ -z "${!name}" ]; then
    echo "ERROR: missing --${name//_/-}" >&2
    exit 2
  fi
done

# cron has no PATH and no login shell
export PATH="$HOME/.pixi/bin:$PATH"
# shellcheck disable=SC1091
[ -r "$HOME/.secrets" ] && . "$HOME/.secrets"
if [ -z "${KIBANA_TOKEN:-}" ] || [ -z "${KIBANA_URI:-}" ]; then
  echo "ERROR: KIBANA_TOKEN and KIBANA_URI must be set in ~/.secrets" >&2
  exit 1
fi

payload="${output_dir}/payload.json"
host="$(cat "${output_dir}/hostname.txt" 2>/dev/null || hostname)"

cd "${AF_BENCH_DIR}" || exit 1

pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
  --job "${job}" \
  --log-type "${log_type}" \
  --log-file "${log_file}" \
  --cluster "${cluster}" \
  --token="${KIBANA_TOKEN}" \
  --kind="benchmark" \
  --host="${host}" \
  --os="${os}" \
  --mode="${mode}" \
  --containerized="${containerized}" \
  --output="${payload}"

# Without this, a failed/crashed ci_parse leaves no payload.json, and curl
# below would silently POST an empty body that still returns HTTP 200 -- a
# false "Upload successful!" with nothing actually in Kibana.
if [ ! -s "${payload}" ]; then
  echo "ERROR: ci_parse did not produce a payload -- see output above"
  exit 1
fi

response=$(curl -X POST "${KIBANA_URI}" \
  -H "Content-Type: application/json" \
  -d @"${payload}" \
  -w "%{http_code}" \
  -s -o "${output_dir}/response.txt")
echo "HTTP Response Code: ${response}"
cat "${output_dir}/response.txt" || true
if [[ ! "${response}" =~ ^2 ]]; then
  echo "Upload failed with HTTP status: ${response}"
  exit 1
fi
echo "Upload successful!"
