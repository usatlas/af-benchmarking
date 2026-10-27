"""append_benchmark, run under real bash, as the benchmark scripts use it."""

import subprocess
from pathlib import Path

from parsing.base_parser import parse_atlas_log

REPO = Path(__file__).resolve().parents[2]
BENCHMARK_UTILS = REPO / "parsing" / "utils" / "benchmark_utils.sh"


def append_benchmark(tmp_path, mode, env=None):
    """Run append_benchmark on an empty log in tmp_path and return the log."""
    log = tmp_path / "job.log"
    log.write_text("")
    subprocess.run(
        [
            "/bin/bash",
            "-c",
            f'source "{BENCHMARK_UTILS}" && append_benchmark job.log '
            f"2026-01-01T00:00:00Z 2026-01-01T00:01:00Z "
            f"2026-01-01T00:00:00Z '' {mode}",
        ],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
        check=True,
    )
    return log


class TestBenchExitStatus:
    def test_sets_exit_status_in_none_mode(self, tmp_path):
        log = append_benchmark(tmp_path, "none", {"BENCH_EXIT_STATUS": "1"})
        assert "exit_status=1\n" in log.read_text()

    def test_none_mode_without_variable_has_no_exit_status(self, tmp_path):
        log = append_benchmark(tmp_path, "none")
        assert "exit_status" not in log.read_text()

    def test_empty_variable_is_ignored(self, tmp_path):
        log = append_benchmark(tmp_path, "none", {"BENCH_EXIT_STATUS": ""})
        assert "exit_status" not in log.read_text()

    def test_parser_reports_failed_status(self, tmp_path):
        log = append_benchmark(tmp_path, "none", {"BENCH_EXIT_STATUS": "1"})
        assert parse_atlas_log(log)["status"] == 1
