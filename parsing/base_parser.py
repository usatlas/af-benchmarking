"""Base parser class for ATLAS benchmark logs.

This module provides common parsing logic shared across different
benchmark types (TRUTH3, EVNT, etc.).
"""

import arrow


def parse_benchmark_block(file_lines):
    """Extract key=value pairs from the LAST === BENCHMARK === block in a log.

    Args:
        file_lines: List of lines from the log file

    Returns:
        dict: All key=value pairs from the last benchmark block,
              or empty dict if no block found
    """
    last_block = {}
    current_block = {}
    in_block = False

    for line in file_lines:
        line = line.strip()
        if line == "=== BENCHMARK ===":
            in_block = True
            current_block = {}
            continue
        if line == "=================" and in_block:
            in_block = False
            last_block = current_block  # keep overwriting — last one wins
            continue
        if in_block and "=" in line:
            key, _, value = line.partition("=")
            current_block[key.strip()] = value.strip()

    return last_block


def parse_atlas_log(path, log_name="ATLAS"):
    """Parse ATLAS benchmark log file for timing information.

    Args:
        path: Path to log file
        log_name: Name of benchmark for logging (e.g., "TRUTH3", "EVNT")

    Returns:
        dict: Parsed timing data with keys:
            - submitTime: UTC timestamp in milliseconds
            - queueTime: Queue time in seconds
            - runTime: Execution time in seconds
            - status: Exit status (0 = success)
    """
    print(f"[{log_name}] Parsing {path.name}")

    with open(path) as f:
        file_lines = f.readlines()

    benchmark = parse_benchmark_block(file_lines)

    if not benchmark:
        raise ValueError(f"[{log_name}] No BENCHMARK block found in {path.name}")

    start_dt = arrow.get(benchmark["start_time_utc"])
    end_dt = arrow.get(benchmark["end_time_utc"])

    if "submit_time_utc" in benchmark:
        submit_dt = arrow.get(benchmark["submit_time_utc"])
        submit_time_ms = submit_dt.int_timestamp * 1000
        queue_time = max(0, int((start_dt - submit_dt).total_seconds()))
    else:
        submit_time_ms = start_dt.int_timestamp * 1000
        queue_time = 0

    result = {
        "submitTime": submit_time_ms,
        "queueTime": queue_time,
        "runTime": int((end_dt - start_dt).total_seconds()),
        "status": int(benchmark.get("exit_status", 0)),
    }

    if "setup_start_time_utc" in benchmark and "setup_end_time_utc" in benchmark:
        setup_start_dt = arrow.get(benchmark["setup_start_time_utc"])
        setup_end_dt = arrow.get(benchmark["setup_end_time_utc"])
        result["setupTime"] = max(0, int((setup_end_dt - setup_start_dt).total_seconds()))

    return result
