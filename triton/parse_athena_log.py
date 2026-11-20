#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import json
from pathlib import Path
from datetime import datetime, timezone
import os
import socket


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Athena log metrics and emit them as JSON."
    )
    parser.add_argument("log_file", help="Path to the Athena log file.")
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Optional output JSON path. Defaults to <log_file with .json>.",
    )
    return parser.parse_args()


def get_node_name() -> str:
    return os.getenv("NODE_NAME", socket.getfqdn())


def calc_avg(pattern: re.Pattern[str], text: str) -> str:
    matches = [float(value) for value in pattern.findall(text)]
    if len(matches) > 1:
        sliced = [value for value in matches[1:9] if value > 0]
    else:
        sliced = [value for value in matches if value > 0]

    if not sliced:
        return "NaN"

    average = sum(sliced) / len(sliced)
    return f"{average:.5f}"


def extract_one(pattern: re.Pattern[str], text: str, default: str = "N/A") -> str:
    m = pattern.search(text)
    if not m:
        return default
    return m.group(1).strip()


def main() -> None:
    args = parse_args()
    log_path = Path(args.log_file)

    if not log_path.is_file():
        raise SystemExit(f"Error: '{log_path}' does not exist or is not a file.")

    text = log_path.read_text(encoding="utf-8", errors="ignore")

    max_rss_pattern = re.compile(r"Max Rss:\s+([\d.]+)(?=\s*GB)")
    eps_pattern = re.compile(r"Events per second:\s+([\d.]+)")
    cpu_pattern = re.compile(r"CPU utilization efficiency \[%\]:\s+([\d.]+)")

    nprocs_pattern = re.compile(r"nprocs = (\d)")

    cpu_model_pattern = re.compile(r"CPU Model:\s+(.+)")
    ncores_pattern = re.compile(r"Number of Available Cores:\s+(\d+)")
    total_memory_pattern = re.compile(r"Total Memory:\s+([\d.]+\s*[A-Z]+)")

    avg_max_rss = float(calc_avg(max_rss_pattern, text))
    avg_events_per_second = float(calc_avg(eps_pattern, text))
    cpu_util_eff = float(calc_avg(cpu_pattern, text))

    nprocs = int(extract_one(nprocs_pattern, text))

    cpu_model = extract_one(cpu_model_pattern, text)
    ncores = int(extract_one(ncores_pattern, text))
    total_memory = extract_one(total_memory_pattern, text)

    print(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(
                    timespec="milliseconds"
                ),
                "average_max_rss_gb": avg_max_rss,
                "average_events_per_second": avg_events_per_second,
                "cpu_utilization_efficiency_percent": cpu_util_eff,
                "nprocs": nprocs,
                # System information
                "node_name": get_node_name(),
                "cpu_model": cpu_model,
                "ncores": ncores,
                "total_memory": total_memory,
            },
            indent=4,
        ),
    )


if __name__ == "__main__":
    main()
