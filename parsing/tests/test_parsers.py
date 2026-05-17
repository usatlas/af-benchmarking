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

    def test_submit_time_utc_sets_submit_time_and_queue_time(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "submit_time_utc=2025-12-08T18:00:00Z\n"
            "start_time_utc=2025-12-08T18:05:00Z\n"
            "end_time_utc=2025-12-08T18:45:00Z\n"
            "exit_status=0\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["submitTime"] == 1765216800000  # submit_time_utc in ms
        assert result["queueTime"] == 300             # 5 minutes in queue
        assert result["runTime"] == 2400              # 40 minutes running

    def test_missing_submit_time_uses_start_time(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:00:30Z\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["submitTime"] == 1765216800000
        assert result["queueTime"] == 0

    def test_setup_times_produce_setup_time(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:30:00Z\n"
            "setup_start_time_utc=2025-12-08T18:00:00Z\n"
            "setup_end_time_utc=2025-12-08T18:02:30Z\n"
            "exit_status=0\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert result["setupTime"] == 150  # 2.5 minutes in seconds

    def test_missing_setup_times_omits_setup_time(self, tmp_path):
        log_file = tmp_path / "log.generate"
        log_file.write_text(
            "=== BENCHMARK ===\n"
            "start_time_utc=2025-12-08T18:00:00Z\n"
            "end_time_utc=2025-12-08T18:00:30Z\n"
            "=================\n"
        )
        result = parse_atlas_log(log_file)
        assert "setupTime" not in result
