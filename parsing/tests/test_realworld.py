"""Integration tests: parse real example logs end-to-end and validate the payload."""

from pathlib import Path

import pytest

from parsing.scripts.ci_parse import parse_log, validate_payload

EXAMPLE_LOGS = Path(__file__).parent.parent / "example-logs"


class TestUcOdfTruth3RealLog:
    @pytest.mark.parametrize("os_name", ["alma9", "centos7"])
    def test_real_truth3_log_validates_for_uc_odf(self, os_name):
        result = parse_log(
            log_file=EXAMPLE_LOGS / "log.Derivation",
            log_type="truth3",
            job="truth3",
            cluster="UC-ODF",
            token="test-token",
            kind="test-kind",
            host="test.example.org",
            payload_file="",
            os=os_name,
            mode="interactive",
            containerized=True,
        )
        validate_payload(result)
        assert result["cluster"] == "UC-ODF"
        assert result["runTime"] == pytest.approx(48.0)


class TestUcOdfEvntAndRucioRealLogs:
    @pytest.mark.parametrize(
        ("log_name", "log_type", "job", "os_name", "expected_run_time"),
        [
            # 18:00:48Z -> 18:41:06Z
            ("log.generate", "evnt", "evnt", "alma9", 2418),
            ("log.generate", "evnt", "evnt", "centos7", 2418),
            # 18:00:22Z -> 18:00:58Z
            ("rucio.log", "rucio", "rucio", "alma9", 36),
        ],
    )
    def test_real_log_validates_for_uc_odf(
        self, log_name, log_type, job, os_name, expected_run_time
    ):
        result = parse_log(
            log_file=EXAMPLE_LOGS / log_name,
            log_type=log_type,
            job=job,
            cluster="UC-ODF",
            token="test-token",
            kind="test-kind",
            host="test.example.org",
            payload_file="",
            os=os_name,
            mode="interactive",
            containerized=True,
        )
        validate_payload(result)
        assert result["cluster"] == "UC-ODF"
        assert result["job"] == job
        assert result["runTime"] == pytest.approx(expected_run_time)
