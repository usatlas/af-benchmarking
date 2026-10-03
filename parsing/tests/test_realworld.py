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
