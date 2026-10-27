"""Run each NERSC job's ALRB `-r "..."` string the way ALRB treats it.

atlasLocalSetup.sh writes the -r payload into an `export ...` line that the
shell evaluates once before anything runs. A runtime `$` in the string would
therefore be expanded early, so the string must survive that extra round of
evaluation unchanged. These tests

1. expand the string the way the host script's double quotes do,
2. run it through that extra `eval "export X=\\"...\\""` round and require the
   result to be identical (the property that a `$` would break), and
3. execute it with stub executables to check the steps run in order, that a
   failed first setup step stops the chain, and that EVNT's host-expanded
   values reach the generator.

macOS and CI have no ALRB, Athena or /usr/bin/time -v, so every external
command is a stub on a temporary PATH. Stubs only record how they were called.
"""

import re
import subprocess
import textwrap
from dataclasses import dataclass

import pytest

from parsing.tests.test_nersc_jobs import JOB_SCRIPTS, REPO, run_option

# The system bash rather than whichever is first on PATH: on macOS that is
# bash 3.2, the oldest the scripts have to work with.
BASH = "/bin/bash"

ISO_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

# Hardcoded paths in the -r strings that do not exist off Perlmutter. They are
# rewritten to stub files before running, which keeps the real `source`
# builtin in play rather than faking it with a shell function.
TIME_PATH = "/usr/bin/time"
FASTFRAMES_SETUP_PATH = "/srv/FastFramesTutorial/TutorialClass/build/setup.sh"


@dataclass(frozen=True)
class Job:
    script: str
    # Names of the stubbed commands the chain should call, in order. The last
    # one is the timed payload.
    calls: tuple
    # The setup command that is made to fail in the failure scenario.
    first_setup: str
    # File that receives the payload's tee'd output.
    tee_file: str
    # File the tee'd output is folded into for append_benchmark (Athena only).
    folded_log: str = None
    # Values the host script defines before expanding the string.
    config_dir: str = None
    seed: str = None


JOBS = [
    Job(
        "TRUTH3/NERSC/EL9/run_truth3_el9_batch.sh",
        calls=("asetup", "Derivation_tf.py"),
        first_setup="asetup",
        tee_file="pipe_file.log",
        folded_log="log.Derivation",
    ),
    Job(
        "TRUTH3/NERSC/CentOS7/run_truth3_centos7_batch.sh",
        calls=("asetup", "Reco_tf.py"),
        first_setup="asetup",
        tee_file="pipe_file.log",
        folded_log="log.EVNTtoDAOD",
    ),
    Job(
        "EVNT/NERSC/EL9/run_evnt_el9_batch.sh",
        calls=("asetup", "Gen_tf.py"),
        first_setup="asetup",
        tee_file="pipe_file.log",
        folded_log="log.generate",
        config_dir="evnt_el9/100xxx/100001",
        seed="1001",
    ),
    Job(
        "EVNT/NERSC/CentOS7/run_evnt_centos7_batch.sh",
        calls=("asetup", "Gen_tf.py"),
        first_setup="asetup",
        tee_file="pipe_file.log",
        folded_log="log.generate",
        config_dir="evnt_centos7/100xxx/100001",
        seed="1001",
    ),
    Job(
        "NTuple_Hist/fastframes/NERSC/run_fastframes.sh",
        calls=("asetup", "setup.sh", "python3"),
        first_setup="asetup",
        tee_file="fastframes.log",
    ),
    Job(
        "NTuple_Hist/coffea/NERSC/run_example.sh",
        calls=("lsetup", "python3", "venv-python", "venv-python", "venv-python"),
        first_setup="lsetup",
        tee_file="coffea_hist.log",
    ),
    Job(
        "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh",
        calls=("lsetup", "asetup", "python3"),
        first_setup="lsetup",
        tee_file="eventloop_arrays.log",
    ),
    Job(
        "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh",
        calls=("lsetup", "asetup", "python3"),
        first_setup="lsetup",
        tee_file="eventloop_noarrays.log",
    ),
]
EVNT_JOBS = [job for job in JOBS if job.config_dir]

# The table above must stay in step with the scripts the other tests cover.
assert [job.script for job in JOBS] == JOB_SCRIPTS


def job_ids(jobs):
    return [job.script for job in jobs]


STUB_TEMPLATE = textwrap.dedent(
    """\
    #!/bin/bash
    # Records one line per call: "<name> setup_complete=<yes|no> <args>". The
    # flag shows whether SETUP_COMPLETE had been written when the call ran.
    if grep -q '^SETUP_COMPLETE=' split.log 2>/dev/null; then
      setup_complete=yes
    else
      setup_complete=no
    fi
    echo "{name} setup_complete=${{setup_complete}} $*" >> "${{STUB_LOG}}"
    if [ "${{STUB_FAIL:-}}" = "{name}" ]; then
      exit 1
    fi
    echo "{name} output"
    """
)

# Mimics `/usr/bin/time -v cmd`: runs cmd, then reports on stderr like time -v.
TIME_STUB = textwrap.dedent(
    """\
    #!/bin/bash
    shift
    "$@"
    status=$?
    echo "Exit status: ${status}" >&2
    exit "${status}"
    """
)


def write_executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def bash_expand(job, tmp_path):
    """Return (host_string, alrb_string) for the job's -r argument.

    host_string is what the host script's double quotes produce. alrb_string
    is that string after ALRB's own `eval "export X=\\"...\\""` round.
    """
    option = run_option((REPO / job.script).read_text())
    definitions = ""
    if job.config_dir:
        definitions = f"config_dir={job.config_dir}\nseed={job.seed}\n"
    script = tmp_path / "expand.sh"
    script.write_text(
        f'{definitions}host_string="{option}"\n'
        'eval "export X=\\"${host_string}\\""\n'
        'printf %s "${host_string}" > host.txt\n'
        'printf %s "${X}" > alrb.txt\n'
    )
    subprocess.run([BASH, str(script)], cwd=tmp_path, check=True)
    return (tmp_path / "host.txt").read_text(), (tmp_path / "alrb.txt").read_text()


@pytest.fixture
def sandbox(tmp_path):
    """Stub executables on a private PATH plus an empty working directory."""
    stubs = tmp_path / "stubs"
    work = tmp_path / "work"
    work.mkdir()
    for name in ("asetup", "lsetup", "Gen_tf.py", "Derivation_tf.py", "Reco_tf.py"):
        write_executable(stubs / name, STUB_TEMPLATE.format(name=name))
    write_executable(stubs / "python3", STUB_TEMPLATE.format(name="python3"))
    write_executable(stubs / "setup.sh", STUB_TEMPLATE.format(name="setup.sh"))
    # The venv is created by `python3 -m venv venv` in the real chain; here
    # python3 is a stub, so the venv's interpreter is provided up front.
    write_executable(
        work / "venv" / "bin" / "python", STUB_TEMPLATE.format(name="venv-python")
    )
    write_executable(stubs / "time", TIME_STUB)
    return tmp_path


def run_chain(job, sandbox, fail=None):
    """Execute the job's ALRB string under bash; return the recorded calls."""
    _, alrb_string = bash_expand(job, sandbox)
    stubs = sandbox / "stubs"
    runnable = alrb_string.replace(TIME_PATH, str(stubs / "time")).replace(
        FASTFRAMES_SETUP_PATH, str(stubs / "setup.sh")
    )
    log = sandbox / "calls.log"
    env = {
        "PATH": f"{stubs}:/usr/bin:/bin",
        "HOME": str(sandbox),
        "STUB_LOG": str(log),
    }
    if fail:
        env["STUB_FAIL"] = fail
    subprocess.run([BASH, "-c", runnable], cwd=sandbox / "work", env=env, check=False)
    return log.read_text().splitlines() if log.exists() else []


def call_names(calls):
    return tuple(call.split()[0] for call in calls)


class TestNerscRunStringsSurviveAlrbEvaluation:
    @pytest.mark.parametrize("job", JOBS, ids=job_ids(JOBS))
    def test_string_is_unchanged_by_the_extra_evaluation(self, job, tmp_path):
        host_string, alrb_string = bash_expand(job, tmp_path)
        assert alrb_string == host_string

    @pytest.mark.parametrize("job", EVNT_JOBS, ids=job_ids(EVNT_JOBS))
    def test_host_values_are_substituted_before_alrb(self, job, tmp_path):
        host_string, _ = bash_expand(job, tmp_path)
        assert f"--jobConfig={job.config_dir} " in host_string
        assert f"--randomSeed={job.seed} " in host_string
        assert "${" not in host_string


class TestNerscRunStringsExecution:
    @pytest.mark.parametrize("job", JOBS, ids=job_ids(JOBS))
    def test_runs_steps_in_order_and_payload_after_setup_complete(self, job, sandbox):
        calls = run_chain(job, sandbox)
        assert call_names(calls) == job.calls
        # Setup steps run before SETUP_COMPLETE is written, the payload after.
        assert all("setup_complete=no" in call for call in calls[:-1])
        assert "setup_complete=yes" in calls[-1]

        split_log = (sandbox / "work" / "split.log").read_text()
        assert re.search(rf"^SETUP_COMPLETE={ISO_UTC}$", split_log, re.M)

    @pytest.mark.parametrize("job", JOBS, ids=job_ids(JOBS))
    def test_payload_output_and_time_report_reach_the_tee_file(self, job, sandbox):
        run_chain(job, sandbox)
        tee_text = (sandbox / "work" / job.tee_file).read_text()
        assert f"{job.calls[-1]} output" in tee_text
        # time -v reports on stderr; 2>&1 must carry it into the tee'd file.
        assert "Exit status: 0" in tee_text

    @pytest.mark.parametrize(
        "job", [job for job in JOBS if job.folded_log], ids=job_ids(JOBS[:4])
    )
    def test_athena_jobs_fold_the_time_report_into_their_log(self, job, sandbox):
        run_chain(job, sandbox)
        assert "Exit status: 0" in (sandbox / "work" / job.folded_log).read_text()

    @pytest.mark.parametrize("job", JOBS, ids=job_ids(JOBS))
    def test_failed_first_setup_step_stops_the_chain(self, job, sandbox):
        calls = run_chain(job, sandbox, fail=job.first_setup)
        assert call_names(calls) == (job.first_setup,)
        split_log = sandbox / "work" / "split.log"
        assert not split_log.exists() or "SETUP_COMPLETE" not in split_log.read_text()
        assert not (sandbox / "work" / job.tee_file).exists()

    @pytest.mark.parametrize("job", EVNT_JOBS, ids=job_ids(EVNT_JOBS))
    def test_evnt_host_values_reach_the_generator(self, job, sandbox):
        calls = run_chain(job, sandbox)
        generator = calls[-1]
        assert f"--jobConfig={job.config_dir}" in generator.split()
        assert f"--randomSeed={job.seed}" in generator.split()
