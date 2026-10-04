"""Integration tests for NERSC/setup_qlei.sh.

The ALRB container launcher is replaced by a stub that records its
arguments, so the directory/copy logic runs for real without cvmfs.
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "NERSC" / "setup_qlei.sh"
DATASET = "user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root"

ALRB_STUB = """#!/bin/bash
printf '%s\\n' "$@" > "$FAKE_LOG/alrb_args"
return "${FAKE_ALRB_STATUS:-0}"
"""


@pytest.fixture
def sandbox(tmp_path):
    alrb = tmp_path / "alrb"
    (alrb / "user").mkdir(parents=True)
    (alrb / "user" / "atlasLocalSetup.sh").write_text(ALRB_STUB)
    home = tmp_path / "home"
    home.mkdir()
    fake_log = tmp_path / "fake_log"
    fake_log.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "SCRATCH": str(tmp_path / "scratch"),
        "CFS_DIR": str(tmp_path / "cfs"),
        "ATLAS_LOCAL_ROOT_BASE": str(alrb),
        "FAKE_LOG": str(fake_log),
    }
    return {"env": env, "tmp": tmp_path, "home": home, "fake_log": fake_log}


def run_setup(sandbox, env_overrides=None):
    env = {**sandbox["env"], **(env_overrides or {})}
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


class TestSetupQleiDirectoriesAndInputs:
    def test_creates_job_directories(self, sandbox):
        result = run_setup(sandbox)
        assert result.returncode == 0, result.stderr
        tmp = sandbox["tmp"]
        for path in [
            "cfs/benchmarks",
            "cfs/wrapper_logs",
            "cfs/fastframes_input",
            "home/af_benchmarking/rucio",
            "scratch/TRUTH3/el9",
            "scratch/TRUTH3/centos7",
            "scratch/EVNT/el9",
            "scratch/EVNT/centos7",
            "scratch/ntuple/coffea/single_campaign_mc20e_dataset_runnable",
            "scratch/ntuple/eventloop_arrays",
            "scratch/ntuple/eventloop_noarrays",
        ]:
            assert (tmp / path).is_dir(), path

    def test_stages_evnt_job_options(self, sandbox):
        run_setup(sandbox)
        for name in ["evnt_el9", "evnt_centos7"]:
            jo = sandbox["home"] / name / "100xxx" / "100001" / "SUSY_Radiative_Decays_JO.py"
            assert jo.is_file(), name

    def test_stages_coffea_and_fastframes_inputs(self, sandbox):
        run_setup(sandbox)
        tmp = sandbox["tmp"]
        assert (
            tmp
            / "scratch/ntuple/coffea/single_campaign_mc20e_dataset_runnable/af_v2_700402.json"
        ).is_file()
        for name in [
            "mc20e_example_config.yml",
            "mc20e_filelist.txt",
            "mc20e_sumweights.txt",
        ]:
            assert (tmp / "cfs" / "fastframes_input" / name).is_file(), name

    def test_rerun_keeps_existing_evnt_copy(self, sandbox):
        run_setup(sandbox)
        marker = sandbox["home"] / "evnt_el9" / "local_edit.txt"
        marker.write_text("keep me\n")
        result = run_setup(sandbox)
        assert result.returncode == 0, result.stderr
        assert marker.read_text() == "keep me\n"
        assert not (sandbox["home"] / "evnt_el9" / "EVNTFiles").exists()

    def test_requires_scratch(self, sandbox):
        env = {k: v for k, v in sandbox["env"].items() if k != "SCRATCH"}
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode != 0
        assert "SCRATCH" in result.stderr


class TestSetupQleiDatasetDownload:
    def test_skips_download_without_passphrase_file(self, sandbox):
        result = run_setup(sandbox)
        assert result.returncode == 0, result.stderr
        assert not (sandbox["fake_log"] / "alrb_args").exists()
        assert "pass.txt" in result.stdout

    def test_downloads_dataset_with_rucio_when_passphrase_present(self, sandbox):
        cfs = sandbox["tmp"] / "cfs"
        (cfs / "benchmarks").mkdir(parents=True)
        (cfs / "benchmarks" / "pass.txt").write_text("secret\n")
        result = run_setup(sandbox)
        assert result.returncode == 0, result.stderr
        args = (sandbox["fake_log"] / "alrb_args").read_text()
        assert "-m\n/global:/global\n" in args
        assert f"rucio download --dir {cfs} user.bhodkins:{DATASET}" in args
        assert "secret" not in args

    def test_reports_failed_download(self, sandbox):
        cfs = sandbox["tmp"] / "cfs"
        (cfs / "benchmarks").mkdir(parents=True)
        (cfs / "benchmarks" / "pass.txt").write_text("secret\n")
        result = run_setup(sandbox, {"FAKE_ALRB_STATUS": "3"})
        assert result.returncode == 3
        assert "download failed (exit 3)" in result.stderr
        assert "Manual steps" in result.stdout
