"""Test suite for benchmark log parsers."""

import pytest

from parsing.base_parser import parse_atlas_log, parse_benchmark_block


class TestParseBenchmarkBlock:
    def test_parses_basic_block(self):
        lines = [
            "some log line\n",
            "=== BENCHMARK ===\n",
            "start_time_utc=2025-12-08T18:00:19Z\n",
            "end_time_utc=2025-12-08T18:01:07Z\n",
            "exit_status=0\n",
            "=================\n",
        ]
        result = parse_benchmark_block(lines)
        assert result == {
            "start_time_utc": "2025-12-08T18:00:19Z",
            "end_time_utc": "2025-12-08T18:01:07Z",
            "exit_status": "0",
        }

    def test_returns_last_block_when_multiple(self):
        lines = [
            "=== BENCHMARK ===\n",
            "start_time_utc=2025-12-08T18:00:00Z\n",
            "end_time_utc=2025-12-08T18:00:30Z\n",
            "exit_status=1\n",
            "=================\n",
            "=== BENCHMARK ===\n",
            "start_time_utc=2025-12-08T18:01:00Z\n",
            "end_time_utc=2025-12-08T18:01:30Z\n",
            "exit_status=0\n",
            "=================\n",
        ]
        result = parse_benchmark_block(lines)
        assert result["start_time_utc"] == "2025-12-08T18:01:00Z"
        assert result["exit_status"] == "0"

    def test_returns_empty_dict_if_no_block(self):
        lines = ["some line\n", "another line\n"]
        assert parse_benchmark_block(lines) == {}

    def test_preserves_extra_fields(self):
        lines = [
            "=== BENCHMARK ===\n",
            "start_time_utc=2025-12-08T18:00:00Z\n",
            "end_time_utc=2025-12-08T18:00:30Z\n",
            "exit_status=0\n",
            "user_time_sec=25.5\n",
            "max_rss_kb=512000\n",
            "=================\n",
        ]
        result = parse_benchmark_block(lines)
        assert result["user_time_sec"] == "25.5"
        assert result["max_rss_kb"] == "512000"


class TestParseAtlasLog:
    def test_parses_timing_fields(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "some header\n"
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:48Z\n"
            "end_time_utc=2025-12-08T18:41:06Z\n"
            "exit_status=0\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["submitTime"] == 1765216848000
        assert result["queueTime"] == 0
        assert result["runTime"] == 2418
        assert result["status"] == 0

    def test_nonzero_exit_status(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:00:30Z\n"
            "exit_status=127\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["status"] == 127

    def test_missing_exit_status_defaults_to_zero(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:00:30Z\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["status"] == 0

    def test_raises_if_no_benchmark_block(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text("some log content without a benchmark block\n")
        with pytest.raises(ValueError, match="No BENCHMARK block"):
            parse_atlas_log(log_file)

    def test_uses_last_benchmark_block(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:00:10Z\n"
            "exit_status=1\n"
            "=================\n"
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:01:00Z\n"
            "end_time_utc=2025-12-08T18:01:45Z\n"
            "exit_status=0\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["submitTime"] == 1765216860000
        assert result["runTime"] == 45
        assert result["status"] == 0
