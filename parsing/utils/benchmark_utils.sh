#!/bin/bash
# benchmark_utils.sh
# Shared utilities for ATLAS benchmark scripts

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
# Usage: append_benchmark <log_file> <start_time> <wall_time_sec> <end_time>
append_benchmark() {
  local log_file=$1
  local start_time=$2
  local wall_time_sec=$3
  local end_time=$4
  local mode=${5:-time_v}

  local extra_metrics=""
  case "${mode}" in
    time_v) extra_metrics=$(extract_time_metrics "${log_file}") ;;
    rucio)  extra_metrics=$(extract_rucio_metrics "${log_file}") ;;
    none)   ;;
  esac

  cat >> "${log_file}" <<EOF
=== BENCHMARK ===
start_time_utc=${start_time}
wall_time_sec=${wall_time_sec}
end_time_utc=${end_time}
${extra_metrics}
=================
EOF
}
