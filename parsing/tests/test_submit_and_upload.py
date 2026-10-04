"""Integration tests for parsing/utils/submit_and_upload.sh.

sbatch and parse_upload.sh are stubs: sbatch records its arguments and the
environment it was given, and optionally creates the job's output directory
the way a real payload script would.
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "parsing" / "utils" / "submit_and_upload.sh"

SBATCH_STUB = r"""#!/bin/bash
printf '%s\n' "$@" > "$FAKE_LOG/sbatch_args"
env > "$FAKE_LOG/sbatch_env"
if [ -n "${FAKE_JOB_OUTPUT:-}" ]; then
  # Real jobs finish minutes after submission; sleep so the new directory is
  # strictly newer than the wrapper's pre-submit marker even on filesystems
  # (or bash builds) with one-second timestamp resolution.
  sleep 1
  mkdir -p "$FAKE_JOB_OUTPUT"
  echo log > "$FAKE_JOB_OUTPUT/log.Derivation"
fi
if [ -z "${FAKE_SBATCH_NO_ID:-}" ]; then
  echo 4242
fi
exit "${FAKE_SBATCH_STATUS:-0}"
"""

PARSE_UPLOAD_STUB = r"""#!/bin/bash
printf '%s\n' "$@" > "$FAKE_LOG/parse_upload_args"
exit "${FAKE_PARSE_STATUS:-0}"
"""


def write_executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


@pytest.fixture
def sandbox(tmp_path):
    utils = tmp_path / "repo" / "parsing" / "utils"
    utils.mkdir(parents=True)
    script = utils / "submit_and_upload.sh"
    shutil.copy(SCRIPT, script)
    write_executable(utils / "parse_upload.sh", PARSE_UPLOAD_STUB)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "sbatch", SBATCH_STUB)
    sub_file = tmp_path / "truth3_el9_sub.sh"
    sub_file.write_text("#!/bin/bash\n")
    benchmarks = tmp_path / "benchmarks"
    benchmarks.mkdir()
    fake_log = tmp_path / "fake_log"
    fake_log.mkdir()
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(fake_log),
    }
    return {
        "env": env,
        "script": script,
        "sub_file": sub_file,
        "benchmarks": benchmarks,
        "fake_log": fake_log,
    }


def default_args(sandbox):
    return [
        "--sub-file",
        str(sandbox["sub_file"]),
        "--output-glob",
        f"{sandbox['benchmarks']}/*/TRUTH3_el9_container",
        "--log-name",
        "log.Derivation",
        "--cluster",
        "NERSC-AF",
        "--job",
        "truth3",
        "--log-type",
        "truth3",
        "--os",
        "alma9",
        "--mode",
        "batch",
        "--containerized",
        "true",
    ]


def run_wrapper(sandbox, args=None, extra_env=None):
    return subprocess.run(
        [
            "bash",
            str(sandbox["script"]),
            *(args if args is not None else default_args(sandbox)),
        ],
        env={**sandbox["env"], **(extra_env or {})},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def new_run_dir(sandbox):
    return sandbox["benchmarks"] / "2026-10-04T06:00:00Z" / "TRUTH3_el9_container"


def old_run_dir(sandbox):
    old = sandbox["benchmarks"] / "2026-10-04T00:00:00Z" / "TRUTH3_el9_container"
    old.mkdir(parents=True)
    an_hour_ago = time.time() - 3600
    os.utime(old, (an_hour_ago, an_hour_ago))
    return old


def recorded(sandbox, name):
    return (sandbox["fake_log"] / name).read_text().splitlines()


class TestSubmitAndUploadSubmission:
    def test_submits_with_wait_and_parsable(self, sandbox):
        run_wrapper(sandbox, extra_env={"FAKE_JOB_OUTPUT": str(new_run_dir(sandbox))})
        assert recorded(sandbox, "sbatch_args") == [
            "--wait",
            "--parsable",
            str(sandbox["sub_file"]),
        ]

    def test_exports_submit_time_and_clears_slurm_vars(self, sandbox):
        run_wrapper(
            sandbox,
            extra_env={
                "FAKE_JOB_OUTPUT": str(new_run_dir(sandbox)),
                "SLURM_JOB_ID": "999",
                "SLURM_CPUS_PER_TASK": "2",
            },
        )
        job_env = recorded(sandbox, "sbatch_env")
        assert not [line for line in job_env if line.startswith("SLURM_")]
        submit = [line for line in job_env if line.startswith("SUBMIT_TIME=")]
        assert len(submit) == 1
        assert re.fullmatch(r"SUBMIT_TIME=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", submit[0])


class TestSubmitAndUploadOutputSelection:
    def test_uploads_this_runs_directory_not_an_older_one(self, sandbox):
        old_run_dir(sandbox)
        new = new_run_dir(sandbox)
        result = run_wrapper(sandbox, extra_env={"FAKE_JOB_OUTPUT": str(new)})
        assert result.returncode == 0, result.stdout + result.stderr
        args = recorded(sandbox, "parse_upload_args")
        assert args[args.index("--output-dir") + 1] == str(new)
        assert args[args.index("--log-file") + 1] == str(new / "log.Derivation")

    def test_forwards_metadata(self, sandbox):
        run_wrapper(sandbox, extra_env={"FAKE_JOB_OUTPUT": str(new_run_dir(sandbox))})
        args = recorded(sandbox, "parse_upload_args")
        for flag, value in [
            ("--cluster", "NERSC-AF"),
            ("--job", "truth3"),
            ("--log-type", "truth3"),
            ("--os", "alma9"),
            ("--mode", "batch"),
            ("--containerized", "true"),
        ]:
            assert args[args.index(flag) + 1] == value

    def test_no_new_directory_means_no_upload(self, sandbox):
        old_run_dir(sandbox)
        result = run_wrapper(sandbox)
        assert result.returncode == 1
        assert "no new output directory" in result.stderr
        assert not (sandbox["fake_log"] / "parse_upload_args").exists()


class TestSubmitAndUploadFailures:
    def test_rejected_submission_skips_upload(self, sandbox):
        result = run_wrapper(
            sandbox, extra_env={"FAKE_SBATCH_STATUS": "1", "FAKE_SBATCH_NO_ID": "1"}
        )
        assert result.returncode == 1
        assert "submission failed" in result.stderr
        assert not (sandbox["fake_log"] / "parse_upload_args").exists()

    def test_nonzero_job_exit_still_uploads_its_output(self, sandbox):
        new = new_run_dir(sandbox)
        result = run_wrapper(
            sandbox,
            extra_env={"FAKE_SBATCH_STATUS": "1", "FAKE_JOB_OUTPUT": str(new)},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "exited 1" in result.stderr
        args = recorded(sandbox, "parse_upload_args")
        assert args[args.index("--output-dir") + 1] == str(new)

    def test_nonzero_job_exit_without_output_fails(self, sandbox):
        result = run_wrapper(sandbox, extra_env={"FAKE_SBATCH_STATUS": "1"})
        assert result.returncode == 1
        assert "no new output directory" in result.stderr
        assert not (sandbox["fake_log"] / "parse_upload_args").exists()

    def test_upload_failure_is_reported(self, sandbox):
        result = run_wrapper(
            sandbox,
            extra_env={
                "FAKE_JOB_OUTPUT": str(new_run_dir(sandbox)),
                "FAKE_PARSE_STATUS": "1",
            },
        )
        assert result.returncode == 1

    def test_missing_sub_file_exits_2(self, sandbox):
        sandbox["sub_file"].unlink()
        result = run_wrapper(sandbox)
        assert result.returncode == 2
        assert not (sandbox["fake_log"] / "sbatch_args").exists()

    def test_flag_without_value_exits_2(self, sandbox):
        result = run_wrapper(sandbox, args=default_args(sandbox)[:-1])
        assert result.returncode == 2

    def test_missing_argument_exits_2(self, sandbox):
        result = run_wrapper(sandbox, args=default_args(sandbox)[2:])
        assert result.returncode == 2
        assert "--sub-file" in result.stderr
