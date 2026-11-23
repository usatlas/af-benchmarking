"""Tests for parsing/utils/benchmark_utils.sh's shell functions.

No ATLAS software required -- these source the script directly and call its
functions against synthetic log text.
"""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UTILS = REPO / "parsing" / "utils" / "benchmark_utils.sh"


def run_extract_rucio_metrics(log_text, tmp_path):
    log_file = tmp_path / "rucio.log"
    log_file.write_text(log_text)
    result = subprocess.run(
        ["bash", "-c", f'source "{UTILS}" && extract_rucio_metrics "{log_file}"'],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return result.stdout


class TestExtractRucioMetrics:
    def test_failed_download_passes_through_a_nonzero_exit_status(self, tmp_path):
        # This is what Rucio/rucio_script.sh's container_el9/native_el9 now
        # write to rucio.log for a failed download -- without this field,
        # base_parser.py's int(benchmark.get("exit_status", 0)) silently
        # defaulted every Rucio run to status 0 (success).
        output = run_extract_rucio_metrics(
            "Total files (DID):                           20\n"
            "Total files (filtered):                      20\n"
            "Downloaded files:                            18\n"
            "Files already found locally:                  0\n"
            "Files that cannot be downloaded:              2\n"
            "exit_status=1\n",
            tmp_path,
        )
        assert "exit_status=1" in output
        assert "rucio_failed_files=2" in output

    def test_successful_download_reports_exit_status_zero(self, tmp_path):
        output = run_extract_rucio_metrics(
            "Total files (DID):                           20\n"
            "Total files (filtered):                      20\n"
            "Downloaded files:                            20\n"
            "Files already found locally:                  0\n"
            "Files that cannot be downloaded:              0\n"
            "exit_status=0\n",
            tmp_path,
        )
        assert "exit_status=0" in output
