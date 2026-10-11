"""Behavioural checks for the files the NERSC host scripts source inside the
ALRB container.

Each container file is sourced under real bash in a temporary working
directory. The ALRB and payload commands (asetup, lsetup, Gen_tf.py, ...) are
stub executables on PATH that append their arguments to a call log, so the
tests can see which steps ran, in what order, and with which arguments.
The static structure checks live in test_nersc_jobs.py.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest

REPO = Path(__file__).resolve().parents[2]

ISO_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

# The container files decide this with `[ -x /usr/bin/time ]`.
HAS_TIME = os.access("/usr/bin/time", os.X_OK)
# BSD time (macOS) exists but has no -v, so it cannot launch the payload.
TIME_V_WORKS = (
    HAS_TIME
    and subprocess.run(
        ["/usr/bin/time", "-v", "true"], capture_output=True, check=False
    ).returncode
    == 0
)
requires_payload = pytest.mark.skipif(
    HAS_TIME and not TIME_V_WORKS,
    reason="/usr/bin/time here does not support -v, so it cannot run the payload",
)

# Every command a container file calls is a stub with one of these names.
# `source` is stubbed because the FastFrames setup script lives under /srv.
STUB_NAMES = [
    "asetup",
    "lsetup",
    "source",
    "python3",
    "Derivation_tf.py",
    "Reco_tf.py",
    "Gen_tf.py",
]

# Logs the call, creates a venv when asked (python3 -m venv <dir>), and fails
# when its own name is in STUB_FAIL. Plain bash 3.2 syntax.
STUB_SCRIPT = """#!/bin/bash
name=$(basename "$0")
echo "$name $*" >> "$STUB_LOG"
if [ "$name" = python3 ] && [ "$1" = -m ] && [ "$2" = venv ]; then
  mkdir -p "$3/bin"
  cp "$0" "$3/bin/python"
fi
case ",$STUB_FAIL," in
  *",$name,"*) exit 1 ;;
esac
echo "output from $name"
"""

# Runs the container file (first argument) the way ALRB's `-r "source ..."`
# does, with the rest of the arguments passed through to it.
RUNNER = """
source() {
  case "$1" in
    /srv/*) "$STUB_BIN/source" "$@" ;;
    *) builtin source "$@" ;;
  esac
}
source "$@"
"""


class Job(NamedTuple):
    container_file: str
    args: tuple
    # Setup commands that stop the file when they fail.
    setup_commands: tuple
    # Substring of the call-log line made by the payload command.
    payload_call: str
    # Log the payload output is appended to, or None if the file does not
    # append to one.
    log_file: str
    # File the payload output is tee'd into.
    tee_file: str


JOBS = {
    "truth3_el9": Job(
        "TRUTH3/NERSC/EL9/truth3_el9_container.sh",
        (),
        ("asetup",),
        "Derivation_tf.py",
        "log.Derivation",
        "pipe_file.log",
    ),
    "truth3_centos7": Job(
        "TRUTH3/NERSC/CentOS7/truth3_centos7_container.sh",
        (),
        ("asetup",),
        "Reco_tf.py",
        "log.EVNTtoDAOD",
        "pipe_file.log",
    ),
    "evnt_el9": Job(
        "EVNT/NERSC/EL9/evnt_el9_container.sh",
        ("my_config/100xxx/100001", "4242"),
        ("asetup",),
        "Gen_tf.py",
        "log.generate",
        "pipe_file.log",
    ),
    "evnt_centos7": Job(
        "EVNT/NERSC/CentOS7/evnt_centos7_container.sh",
        ("my_config/100xxx/100001", "4242"),
        ("asetup",),
        "Gen_tf.py",
        "log.generate",
        "pipe_file.log",
    ),
    "fastframes": Job(
        "NTuple_Hist/fastframes/NERSC/fastframes_container.sh",
        (),
        ("asetup", "source"),
        "FastFrames.py",
        None,
        "fastframes.log",
    ),
    # `python3 -m venv` is the venv step; the venv's own `python` runs pip
    # and then the payload.
    "coffea": Job(
        "NTuple_Hist/coffea/NERSC/coffea_container.sh",
        (),
        ("lsetup", "python3", "python"),
        "example.py",
        None,
        "coffea_hist.log",
    ),
    "eventloop_arrays": Job(
        "NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_container.sh",
        (),
        ("lsetup", "asetup"),
        "event_loop_arrays.py",
        None,
        "eventloop_arrays.log",
    ),
    "eventloop_noarrays": Job(
        "NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_container.sh",
        (),
        ("lsetup", "asetup"),
        "event_loop_noarrays.py",
        None,
        "eventloop_noarrays.log",
    ),
}
ALL_JOBS = pytest.mark.parametrize("job", JOBS.values(), ids=JOBS.keys())
ATHENA_JOBS = pytest.mark.parametrize(
    "job", [j for j in JOBS.values() if j.log_file], ids=lambda j: j.log_file
)
EVNT_JOBS = pytest.mark.parametrize(
    "job", [JOBS["evnt_el9"], JOBS["evnt_centos7"]], ids=["el9", "centos7"]
)


class Run:
    """Result of sourcing a container file in a scratch directory."""

    def __init__(self, process, work_dir, call_log):
        self.returncode = process.returncode
        self.stderr = process.stderr
        self.work_dir = work_dir
        self.calls = call_log.read_text().splitlines() if call_log.exists() else []

    def read(self, name):
        path = self.work_dir / name
        return path.read_text() if path.exists() else ""

    def payload_calls(self, job):
        return [call for call in self.calls if job.payload_call in call]


def run_container(tmp_path, job, failing_command=""):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in STUB_NAMES:
        stub = bin_dir / name
        stub.write_text(STUB_SCRIPT)
        stub.chmod(0o755)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    call_log = tmp_path / "calls.log"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "STUB_BIN": str(bin_dir),
        "STUB_LOG": str(call_log),
        "STUB_FAIL": failing_command,
    }
    process = subprocess.run(
        ["bash", "-c", RUNNER, "_", str(REPO / job.container_file), *job.args],
        cwd=work_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return Run(process, work_dir, call_log)


SETUP_FAILURES = [
    pytest.param(job, command, id=f"{name}-{command}")
    for name, job in JOBS.items()
    for command in job.setup_commands
]


class TestSetupFailureStopsTheJob:
    @pytest.mark.parametrize("job,failing_command", SETUP_FAILURES)
    def test_no_markers_and_no_payload(self, tmp_path, job, failing_command):
        run = run_container(tmp_path, job, failing_command)

        assert run.returncode != 0
        assert "SETUP_COMPLETE=" not in run.read("split.log")
        assert "BENCH_MODE=" not in run.read("split.log")
        assert run.payload_calls(job) == []
        assert any(call.startswith(failing_command) for call in run.calls)


class TestSuccessfulRun:
    @ALL_JOBS
    def test_records_setup_complete_and_bench_mode(self, tmp_path, job):
        run = run_container(tmp_path, job)
        split_log = run.read("split.log")

        assert run.returncode == 0, run.stderr
        assert re.search(rf"^SETUP_COMPLETE={ISO_UTC}$", split_log, re.M)
        expected_mode = "time_v" if HAS_TIME else "none"
        assert f"BENCH_MODE={expected_mode}\n" in split_log

    @requires_payload
    @ALL_JOBS
    def test_runs_payload_after_setup(self, tmp_path, job):
        run = run_container(tmp_path, job)

        assert run.returncode == 0, run.stderr
        assert len(run.payload_calls(job)) == 1
        payload_index = next(
            i for i, call in enumerate(run.calls) if job.payload_call in call
        )
        assert payload_index == len(run.calls) - 1

    @requires_payload
    @ALL_JOBS
    def test_tee_file_holds_payload_output(self, tmp_path, job):
        run = run_container(tmp_path, job)

        assert "output from" in run.read(job.tee_file)

    @requires_payload
    @pytest.mark.skipif(not HAS_TIME, reason="no /usr/bin/time")
    @ALL_JOBS
    def test_time_v_report_reaches_tee_file(self, tmp_path, job):
        run = run_container(tmp_path, job)

        assert "Maximum resident set size" in run.read(job.tee_file)

    @requires_payload
    @ATHENA_JOBS
    def test_tee_output_is_appended_to_athena_log(self, tmp_path, job):
        run = run_container(tmp_path, job)

        assert run.read(job.tee_file) != ""
        assert run.read(job.log_file) == run.read(job.tee_file)


class TestEvntArguments:
    @requires_payload
    @EVNT_JOBS
    def test_config_dir_and_seed_reach_the_payload(self, tmp_path, job):
        run = run_container(tmp_path, job)

        (payload,) = run.payload_calls(job)
        assert "--jobConfig=my_config/100xxx/100001 " in payload + " "
        assert "--randomSeed=4242 " in payload + " "
