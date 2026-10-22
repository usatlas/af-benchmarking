"""Tests for the per-job SLAC submit_and_upload.sh wrappers.

Each wrapper keeps only what is SLAC-specific (the flock that stops
overlapping cron runs, and the cd/cleanup of the job's working directory)
and execs the shared parsing/utils/submit_and_upload.sh for submission,
waiting, output-directory selection and upload.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SHARED_WRAPPER = '"${AF_BENCH_DIR}/parsing/utils/submit_and_upload.sh"'

# wrapper -> (job, log_type, os, log_name, job_output_name, cleans_job_dir)
WRAPPERS = {
    "TRUTH3/SLAC/EL9/submit_and_upload.sh": (
        "truth3",
        "truth3",
        "alma9",
        "log.Derivation",
        "TRUTH3_el9_container",
        True,
    ),
    "TRUTH3/SLAC/CentOS7/submit_and_upload.sh": (
        "truth3",
        "truth3",
        "centos7",
        "log.EVNTtoDAOD",
        "TRUTH3_centos7_container",
        True,
    ),
    "EVNT/SLAC/EL9/submit_and_upload.sh": (
        "evnt",
        "evnt",
        "alma9",
        "log.generate",
        "EVNT_container_el",
        True,
    ),
    "EVNT/SLAC/CentOS7/submit_and_upload.sh": (
        "evnt",
        "evnt",
        "centos7",
        "log.generate",
        "EVNT_container_centos",
        True,
    ),
    "NTuple_Hist/coffea/SLAC/submit_and_upload.sh": (
        "coffea",
        "coffea",
        "alma9",
        "coffea_hist.log",
        "Coffea_Hist",
        False,
    ),
    "NTuple_Hist/fastframes/SLAC/submit_and_upload.sh": (
        "fastframes",
        "fastframes",
        "alma9",
        "fastframes.log",
        "FastFrames_Hist",
        False,
    ),
    "NTuple_Hist/event_loop/SLAC/columnar/submit_and_upload.sh": (
        "eventloop-columnar",
        "eventloop",
        "alma9",
        "event_loop_arrays.log",
        "eventloop_arrays",
        False,
    ),
    "NTuple_Hist/event_loop/SLAC/standard/submit_and_upload.sh": (
        "eventloop-standard",
        "eventloop",
        "alma9",
        "event_loop_noarrays.log",
        "eventloop_noarrays",
        False,
    ),
}


def wrapper_text(wrapper):
    return (REPO / wrapper).read_text()


class TestSlacWrapperStructure:
    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_execs_shared_wrapper(self, wrapper):
        assert f"exec {SHARED_WRAPPER}" in wrapper_text(wrapper)

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_locks_and_enters_job_dir_before_exec(self, wrapper):
        # exec keeps fd 200 open, so the lock is held until the shared
        # wrapper exits; taking it after the exec would never happen.
        text = wrapper_text(wrapper)
        exec_at = text.index(f"exec {SHARED_WRAPPER}")
        assert text.index("flock -n 200") < exec_at
        assert text.index('cd "${job_dir}"') < exec_at

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_leaves_submission_and_upload_to_shared_wrapper(self, wrapper):
        text = wrapper_text(wrapper)
        assert "sbatch" not in re.sub(r"#.*", "", text)
        assert "parse_upload.sh" not in text
        assert "find_latest_output_dir" not in text

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_bash_syntax(self, wrapper):
        result = subprocess.run(
            ["bash", "-n", str(REPO / wrapper)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


FLOCK_STUB = """#!/bin/bash
printf '%s\\n' "$@" > "$FAKE_LOG/flock_args"
"""

SHARED_STUB = """#!/bin/bash
pwd > "$FAKE_LOG/shared_cwd"
printf '%s\\n' "$@" > "$FAKE_LOG/shared_args"
"""


@pytest.fixture
def sandbox(tmp_path):
    """A fake repo whose shared wrapper records its arguments and cwd."""
    utils = tmp_path / "repo" / "parsing" / "utils"
    utils.mkdir(parents=True)
    (utils / "submit_and_upload.sh").write_text(SHARED_STUB)
    (utils / "submit_and_upload.sh").chmod(0o755)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "flock").write_text(FLOCK_STUB)
    (bin_dir / "flock").chmod(0o755)
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "previous_run.txt").write_text("stale\n")
    log = tmp_path / "log"
    log.mkdir()
    return tmp_path


def run_wrapper(sandbox, wrapper):
    """Run a copy of the wrapper with its repo and job_dir moved into sandbox."""
    text = wrapper_text(wrapper)
    text = re.sub(
        r"^readonly AF_BENCH_DIR=.*$",
        f'readonly AF_BENCH_DIR="{sandbox / "repo"}"',
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^readonly job_dir=.*$",
        f'readonly job_dir="{sandbox / "job"}"',
        text,
        flags=re.M,
    )
    copy = sandbox / "wrapper.sh"
    copy.write_text(text)
    return subprocess.run(
        ["bash", str(copy)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{sandbox / 'bin'}:/usr/bin:/bin",
            "HOME": str(sandbox),
            "USER": "qlei",
            "FAKE_LOG": str(sandbox / "log"),
        },
    )


class TestSlacWrapperRun:
    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_passes_job_settings_to_shared_wrapper(self, sandbox, wrapper):
        job, log_type, os_name, log_name, output_name, _ = WRAPPERS[wrapper]
        result = run_wrapper(sandbox, wrapper)
        assert result.returncode == 0, result.stderr
        args = (sandbox / "log" / "shared_args").read_text().splitlines()
        options = dict(zip(args[::2], args[1::2]))
        sub_file = options.pop("--sub-file")
        assert sub_file.startswith(str(sandbox / "repo") + "/")
        assert (REPO / sub_file.removeprefix(str(sandbox / "repo") + "/")).is_file()
        assert options == {
            "--output-glob": f"/sdf/data/atlas/u/qlei/benchmarks/*/{output_name}",
            "--log-name": log_name,
            "--cluster": "SLAC-AF",
            "--job": job,
            "--log-type": log_type,
            "--os": os_name,
            "--mode": "batch",
            "--containerized": "true",
        }

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_submits_from_job_dir_under_lock(self, sandbox, wrapper):
        result = run_wrapper(sandbox, wrapper)
        assert result.returncode == 0, result.stderr
        assert (sandbox / "log" / "flock_args").read_text().split() == ["-n", "200"]
        cwd = (sandbox / "log" / "shared_cwd").read_text().strip()
        assert Path(cwd).resolve() == (sandbox / "job").resolve()

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_cleans_job_dir_only_where_configured(self, sandbox, wrapper):
        cleans = WRAPPERS[wrapper][5]
        result = run_wrapper(sandbox, wrapper)
        assert result.returncode == 0, result.stderr
        assert (sandbox / "job" / "previous_run.txt").exists() is not cleans
