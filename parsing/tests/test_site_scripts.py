"""Tests for the per-site benchmark shell scripts (no ATLAS software required)."""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestRucioScriptOdfSite:
    def test_odf_is_a_known_site(self, tmp_path):
        # HOME points at an empty temp dir so container_el9 fails at its first
        # `cd` into $HOME/af_benchmarking/rucio/ and never reaches setupATLAS or
        # the download. The test only checks the site dispatch.
        result = subprocess.run(
            ["bash", "Rucio/rucio_script.sh", "odf"],
            cwd=REPO_ROOT,
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout + result.stderr
        assert "Running for site: odf" in output
        assert "Unknown site" not in output


class TestUcOdfEvntScripts:
    @pytest.mark.parametrize(
        "script",
        [
            "EVNT/UC-ODF/EL9_i/run_evnt_el9_interactive.sh",
            "EVNT/UC-ODF/CentOS7_i/run_evnt_centos7_interactive.sh",
        ],
    )
    def test_script_is_executable_and_valid_bash(self, script):
        path = REPO_ROOT / script
        assert path.is_file()
        assert os.access(path, os.X_OK)
        # -n parses the script without running it
        subprocess.run(["bash", "-n", str(path)], check=True)
