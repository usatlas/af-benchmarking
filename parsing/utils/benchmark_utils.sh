#!/bin/bash
# benchmark_utils.sh
# Shared utilities for ATLAS benchmark scripts

# Sets TIME_CMD (array) and bench_mode in the caller's scope depending on
# whether /usr/bin/time -v is available in this container -- so
# append_benchmark is never asked to extract metrics from output that was
# never produced.
# Usage: set_time_cmd (sets TIME_CMD, bench_mode in the caller's scope)
set_time_cmd() {
  if [ -x /usr/bin/time ]; then
    # shellcheck disable=SC2034 # consumed by the caller, not this file
    TIME_CMD=(/usr/bin/time -v)
    bench_mode=time_v
  else
    # shellcheck disable=SC2034 # consumed by the caller, not this file
    TIME_CMD=()
    # shellcheck disable=SC2034 # consumed by the caller, not this file
    bench_mode=none
  fi
}

# Finds the most recently modified directory named <job_output_name> under
# <log_base> (mirrors TRUTH3/BNL/EL9/cron_el_batch.sh:52, adapted: Slurm
# gives us no direct equivalent of HTCondor's per-cluster log path). Exits
# the caller if none is found.
# Usage: latest_dir=$(find_latest_output_dir <log_base> <job_output_name>)
find_latest_output_dir() {
  local log_base=$1
  local job_output_name=$2
  local dir
  dir=$(find "${log_base}" -mindepth 2 -maxdepth 2 -type d -name "${job_output_name}" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')
  if [ -z "${dir}" ]; then
    echo "ERROR: no ${job_output_name} directory found under ${log_base}" >&2
    exit 1
  fi
  echo "Latest output directory: ${dir}" >&2
  echo "${dir}"
}

# Parse /usr/bin/time -v output from a log file and extract key metrics
# Usage: extract_time_metrics <log_file>
extract_time_metrics() {
  local log_file=$1

  grep -E "User time|System time|Percent of CPU|Elapsed \(wall clock\)|Maximum resident set size|Major \(requiring I/O\)|Minor \(reclaiming|Voluntary context|Involuntary context|Exit status" "${log_file}" | \
  awk -F': ' '
    /User time/              { user=$2 }
    /System time/            { sys=$2 }
    /Percent of CPU/         { cpu=$2; gsub(/%/,"",cpu) }
    /Elapsed \(wall clock\)/ { elapsed=$2 }
    /Maximum resident set/   { maxrss=$2 }
    /Major.*page faults/     { majflt=$2 }
    /Minor.*page faults/     { minflt=$2 }
    /Voluntary context/      { vcswitch=$2 }
    /Involuntary context/    { ivcswitch=$2 }
    /Exit status/            { exit_status=$2 }
    END {
      print "user_time_sec=" user
      print "sys_time_sec=" sys
      print "cpu_percent=" cpu
      print "elapsed_time=" elapsed
      print "max_rss_kb=" maxrss
      print "major_page_faults=" majflt
      print "minor_page_faults=" minflt
      print "voluntary_ctx_switches=" vcswitch
      print "involuntary_ctx_switches=" ivcswitch
      print "exit_status=" exit_status
    }
  '
}

# Parse rucio download metrics from a rucio.log file
# Usage: extract_rucio_metrics <log_file>
extract_rucio_metrics() {
  local log_file=$1

  awk '
    /Total files \(DID\)/              { total_did=$NF }
    /Total files \(filtered\)/         { total_filtered=$NF }
    /Downloaded files/                 { downloaded=$NF }
    /Files already found locally/      { already_local=$NF }
    /Files that cannot be downloaded/  { failed=$NF }
    /^[0-9]+[[:space:]]/               { du_kb=$1 }
    END {
      print "rucio_total_files_did=" total_did
      print "rucio_total_files_filtered=" total_filtered
      print "rucio_downloaded_files=" downloaded
      print "rucio_already_local=" already_local
      print "rucio_failed_files=" failed
      print "rucio_du_kb=" du_kb
    }
  ' "${log_file}"
}

# Append standardized benchmark block to a log file
# Usage: append_benchmark <log_file> <start_time> <end_time> [setup_start] [setup_end] [mode]
# Reads SUBMIT_TIME from environment if set (injected by cron/submit scripts via HTCondor).
# Reads BENCH_EXIT_STATUS from environment if set (meant for mode "none", where there is
# no time -v report to take the exit status from, e.g. a run that failed before its payload).
append_benchmark() {
  local log_file=$1
  local start_time=$2
  local end_time=$3
  local setup_start=${4:-}
  local setup_end=${5:-}
  local mode=${6:-time_v}

  local extra_metrics=""
  case "${mode}" in
    time_v) extra_metrics=$(extract_time_metrics "${log_file}") ;;
    rucio)  extra_metrics=$(extract_rucio_metrics "${log_file}") ;;
    none)   ;;
  esac

  {
    echo "=== BENCHMARK ==="
    [[ -n "${SUBMIT_TIME:-}" ]] && echo "submit_time_utc=${SUBMIT_TIME}"
    echo "start_time_utc=${start_time}"
    echo "end_time_utc=${end_time}"
    [[ -n "${setup_start}" ]] && echo "setup_start_time_utc=${setup_start}"
    [[ -n "${setup_end}" ]] && echo "setup_end_time_utc=${setup_end}"
    [[ -n "${extra_metrics}" ]] && printf '%s\n' "${extra_metrics}"
    [[ -n "${BENCH_EXIT_STATUS:-}" ]] && echo "exit_status=${BENCH_EXIT_STATUS}"
    echo "================="
  } >> "${log_file}"
}
