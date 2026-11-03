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


SUB_FILES = [
    "TRUTH3/SLAC/EL9/truth3_el9_sub.sh",
    "TRUTH3/SLAC/CentOS7/truth3_centos7_sub.sh",
    "EVNT/SLAC/EL9/evnt_el9_sub.sh",
    "EVNT/SLAC/CentOS7/evnt_centos7_sub.sh",
    "NTuple_Hist/coffea/SLAC/coffea_el9_sub.sh",
    "NTuple_Hist/fastframes/SLAC/fastframes_el9_sub.sh",
    "NTuple_Hist/event_loop/SLAC/columnar/event_loop_arrays.sh",
    "NTuple_Hist/event_loop/SLAC/standard/event_loop_noarrays.sh",
]


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
exit "$FAKE_FLOCK_STATUS"
"""

SHARED_STUB = """#!/bin/bash
# fd 200 still open here means exec carried the lock into this process.
[ -e /dev/fd/200 ] && touch "$FAKE_LOG/lock_fd_open"
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


def run_wrapper(sandbox, wrapper, flock_status=0):
    """Run a copy of the wrapper with its repo and job_dir moved into sandbox."""
    text = wrapper_text(wrapper)
    # Both must be redirected: several job_dirs are absolute /sdf paths that
    # the TRUTH3/EVNT wrappers empty with rm -rf, so a silent miss here would
    # delete a real job directory if the suite ran on a SLAC host.
    for name, value in [
        ("AF_BENCH_DIR", sandbox / "repo"),
        ("job_dir", sandbox / "job"),
    ]:
        text, count = re.subn(
            rf"^readonly {name}=.*$", f'readonly {name}="{value}"', text, flags=re.M
        )
        assert count == 1, f"{wrapper}: expected one readonly {name} line"
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
            "FAKE_FLOCK_STATUS": str(flock_status),
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
        assert (sandbox / "log" / "lock_fd_open").exists()
        cwd = (sandbox / "log" / "shared_cwd").read_text().strip()
        assert Path(cwd).resolve() == (sandbox / "job").resolve()

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_busy_lock_exits_without_touching_job_dir(self, sandbox, wrapper):
        result = run_wrapper(sandbox, wrapper, flock_status=1)
        assert result.returncode == 1
        assert "already running" in result.stdout
        assert not (sandbox / "log" / "shared_args").exists()
        assert (sandbox / "job" / "previous_run.txt").exists()

    @pytest.mark.parametrize("wrapper", WRAPPERS)
    def test_cleans_job_dir_only_where_configured(self, sandbox, wrapper):
        cleans = WRAPPERS[wrapper][5]
        result = run_wrapper(sandbox, wrapper)
        assert result.returncode == 0, result.stderr
        assert (sandbox / "job" / "previous_run.txt").exists() is not cleans


ALRB_STUB = """#!/bin/bash
printf '%s' "${APPTAINERENV_SUBMIT_TIME-<unset>}" > "$FAKE_LOG/apptainerenv_submit_time"
"""


def run_sub_file(tmp_path, sub_file, env_extra):
    """Run a copy of the sub file against a stub atlasLocalSetup.sh."""
    alrb = tmp_path / "alrb"
    (alrb / "user").mkdir(parents=True)
    (alrb / "user" / "atlasLocalSetup.sh").write_text(ALRB_STUB)
    log = tmp_path / "log"
    log.mkdir()
    text, count = re.subn(
        r"^export ATLAS_LOCAL_ROOT_BASE=.*$",
        f'export ATLAS_LOCAL_ROOT_BASE="{alrb}"',
        (REPO / sub_file).read_text(),
        flags=re.M,
    )
    assert count == 1, f"{sub_file}: expected one ATLAS_LOCAL_ROOT_BASE line"
    copy = tmp_path / "sub.sh"
    copy.write_text(text)
    result = subprocess.run(
        ["bash", str(copy)],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "FAKE_LOG": str(log)}
        | env_extra,
    )
    assert result.returncode == 0, result.stderr
    return (log / "apptainerenv_submit_time").read_text()


class TestSlacSubFileSubmitTime:
    # ALRB runs the payload with `apptainer exec -e` (clean environment), so
    # a plain SUBMIT_TIME never reaches append_benchmark inside the
    # container; APPTAINERENV_SUBMIT_TIME is set as SUBMIT_TIME inside.
    @pytest.mark.parametrize("sub_file", SUB_FILES)
    def test_passes_submit_time_into_container(self, tmp_path, sub_file):
        submit_time = "2026-10-26T17:14:00Z"
        env = {"SUBMIT_TIME": submit_time}
        assert run_sub_file(tmp_path, sub_file, env) == submit_time

    @pytest.mark.parametrize("sub_file", SUB_FILES)
    def test_manual_submission_passes_empty_submit_time(self, tmp_path, sub_file):
        # Empty inside the container, so append_benchmark omits the line.
        assert run_sub_file(tmp_path, sub_file, {}) == ""
