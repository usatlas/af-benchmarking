"""Static checks that each NERSC payload script follows the benchmark
conventions: it writes an append_benchmark block before moving its log, and
records the compute node's hostname for the login-node upload step.

The in-container steps live in a sourced file next to each host script, not in
the ALRB `-r "..."` string: ALRB evaluates every `$` in that string once,
before running any of it, so container-side variables and `$(date)` calls
written there never behave as written.

These scripts only run under ALRB on Perlmutter, so their behavior is
validated there; these checks pin the structure that validation relies on.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

JOB_SCRIPTS = [
    "TRUTH3/NERSC/EL9/run_truth3_el9_batch.sh",
    "TRUTH3/NERSC/CentOS7/run_truth3_centos7_batch.sh",
    "EVNT/NERSC/EL9/run_evnt_el9_batch.sh",
    "EVNT/NERSC/CentOS7/run_evnt_centos7_batch.sh",
    "NTuple_Hist/fastframes/NERSC/run_fastframes.sh",
    "NTuple_Hist/coffea/NERSC/run_example.sh",
    "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh",
    "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh",
]

# Host script -> the file it sources inside the ALRB container. Each family is
# listed once its steps have moved out of the `-r` string.
CONTAINER_FILES = {
    "TRUTH3/NERSC/EL9/run_truth3_el9_batch.sh": "TRUTH3/NERSC/EL9/truth3_el9_container.sh",
    "TRUTH3/NERSC/CentOS7/run_truth3_centos7_batch.sh": "TRUTH3/NERSC/CentOS7/truth3_centos7_container.sh",
    "EVNT/NERSC/EL9/run_evnt_el9_batch.sh": "EVNT/NERSC/EL9/evnt_el9_container.sh",
    "EVNT/NERSC/CentOS7/run_evnt_centos7_batch.sh": "EVNT/NERSC/CentOS7/evnt_centos7_container.sh",
    "NTuple_Hist/fastframes/NERSC/run_fastframes.sh": "NTuple_Hist/fastframes/NERSC/fastframes_container.sh",
    "NTuple_Hist/coffea/NERSC/run_example.sh": "NTuple_Hist/coffea/NERSC/coffea_container.sh",
    "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh": "NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_container.sh",
    "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh": "NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_container.sh",
}

# Host-expanded values a host script passes to its container file.
EVNT_ARGS = " ${config_dir} ${seed}"
SOURCE_ARGS = {
    "EVNT/NERSC/EL9/run_evnt_el9_batch.sh": EVNT_ARGS,
    "EVNT/NERSC/CentOS7/run_evnt_centos7_batch.sh": EVNT_ARGS,
}

# Every NERSC job is submitted through sbatch; each payload needs a sub file.
SUB_FILES = {
    "NTuple_Hist/coffea/NERSC/coffea_el9_sub.sh": "NTuple_Hist/coffea/NERSC/run_example.sh",
    "NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_sub.sh": "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh",
    "NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_sub.sh": "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh",
}


@pytest.fixture(params=JOB_SCRIPTS)
def script_text(request):
    return (REPO / request.param).read_text()


@pytest.fixture(params=CONTAINER_FILES.items(), ids=list(CONTAINER_FILES))
def host_and_container(request):
    host, container = request.param
    return host, container, (REPO / host).read_text()


@pytest.fixture(params=CONTAINER_FILES.values())
def container_text(request):
    return (REPO / request.param).read_text()


def run_option(script_text):
    """Body of the double-quoted, possibly backslash-continued -r argument.

    Anchored to the atlasLocalSetup.sh line so other `-r` options (cp -r) are
    not mistaken for it.
    """
    # re.S so `\.` also consumes the newline of a backslash continuation.
    match = re.search(
        r'atlasLocalSetup\.sh[^\n]* -r "((?:[^"\\]|\\.)*)"', script_text, re.S
    )
    assert match, "no -r argument found"
    return match.group(1)


class TestNerscJobScriptBenchmarkConventions:
    def test_sources_benchmark_utils(self, script_text):
        assert (
            'source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh'
            in script_text
        )

    def test_reads_setup_end_and_mode_back(self, script_text):
        assert 'grep "^SETUP_COMPLETE=" split.log' in script_text
        assert 'grep "^BENCH_MODE=" split.log' in script_text

    def test_records_compute_node_hostname(self, script_text):
        assert re.search(r'^hostname > "\$\{\w+\}/hostname\.txt"$', script_text, re.M)

    def test_appends_benchmark_before_moving_log(self, script_text):
        append = re.search(r"^append_benchmark ", script_text, re.M)
        first_mv = re.search(r"^mv ", script_text, re.M)
        assert append and first_mv
        assert append.start() < first_mv.start()
        assert '"${bench_mode:-none}"' in script_text[append.start() :]

    def test_payload_stderr_reaches_log(self, script_text):
        assert "2>1|" not in script_text


class TestNerscContainerFiles:
    def test_every_job_script_has_a_container_file(self):
        assert set(CONTAINER_FILES) == set(JOB_SCRIPTS)

    def test_host_sources_container_file(self, host_and_container):
        host, container, host_text = host_and_container
        expected = (
            f"source ${{HOME}}/AF-Benchmarking/{container}{SOURCE_ARGS.get(host, '')}"
        )
        assert run_option(host_text) == expected
        assert (REPO / container).is_file()

    def test_run_option_has_no_escaped_dollar(self, host_and_container):
        # `\$` in a -r string is expanded early by ALRB, not at container time.
        assert "\\$" not in run_option(host_and_container[2])

    def test_container_file_is_sourced_not_executed(self, container_text):
        assert container_text.startswith("# shellcheck shell=bash\n")
        assert not re.search(r"^\s*exit\b", container_text, re.M)

    def test_guards_time_v(self, container_text):
        assert "if [ -x /usr/bin/time ]" in container_text

    def test_records_setup_complete_when_it_happens(self, container_text):
        assert (
            """echo "SETUP_COMPLETE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> split.log"""
            in container_text
        )

    def test_records_bench_mode(self, container_text):
        assert 'echo "BENCH_MODE=${BENCH_MODE}" >> split.log' in container_text

    def test_payload_stderr_reaches_log(self, container_text):
        assert "2>1|" not in container_text


class TestNerscJobsAreSubmittable:
    @pytest.mark.parametrize("sub_file,payload", SUB_FILES.items())
    def test_sub_file_runs_payload(self, sub_file, payload):
        text = (REPO / sub_file).read_text()
        assert "#SBATCH -q regular" in text
        assert f'"$HOME"/AF-Benchmarking/{payload}' in text


class TestRucioContainerFunction:
    def test_container_el9_records_hostname(self):
        text = (REPO / "Rucio" / "rucio_script.sh").read_text()
        body = text.split("container_el9 (){", 1)[1].split("\n}\n", 1)[0]
        assert 'hostname > "${3}/hostname.txt"' in body

    def test_nersc_branch_sources_benchmark_utils(self):
        # append_benchmark runs inside container_el9, so the case branch must
        # source it before the call. $HOME because the sub file cds into Rucio/.
        text = (REPO / "Rucio" / "rucio_script.sh").read_text()
        branch = text.split("\n    nersc)", 1)[1].split(";;", 1)[0]
        assert (
            'source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh' in branch
        )
