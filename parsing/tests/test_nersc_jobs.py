"""Static checks that each NERSC payload script follows the benchmark
conventions: it writes an append_benchmark block before moving its log, and
records the compute node's hostname for the login-node upload step.

The in-container steps are inline in the ALRB `-r "..."` string and contain
no runtime `$`: ALRB evaluates every `$` in that string once, before running
any of it, so container-side variables and `$(date)` calls written there never
behave as written.

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

ATHENA_JOB_SCRIPTS = JOB_SCRIPTS[:4]

# Values the host expands into the -r string before ALRB sees it.
HOST_EXPANDED_VALUES = {
    "EVNT/NERSC/EL9/run_evnt_el9_batch.sh": ("${config_dir}", "${seed}"),
    "EVNT/NERSC/CentOS7/run_evnt_centos7_batch.sh": ("${config_dir}", "${seed}"),
}

# Every NERSC job is submitted through sbatch; each payload needs a sub file.
SUB_FILES = {
    "NTuple_Hist/coffea/NERSC/coffea_el9_sub.sh": "NTuple_Hist/coffea/NERSC/run_example.sh",
    "NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_sub.sh": "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh",
    "NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_sub.sh": "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh",
}


@pytest.fixture(params=JOB_SCRIPTS)
def script(request):
    return request.param


@pytest.fixture
def script_text(script):
    return (REPO / script).read_text()


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

    def test_reads_setup_end_back(self, script_text):
        assert 'grep "^SETUP_COMPLETE=" split.log' in script_text

    def test_has_no_bench_mode_variable_from_container(self, script_text):
        # The mode is decided on the host from setup_end, not read back from
        # the container.
        assert "BENCH_MODE" not in script_text
        assert 'grep "^BENCH_MODE=' not in script_text

    def test_failed_setup_is_recorded_as_failed_run(self, script_text):
        assert (
            "bench_mode=time_v\n"
            "# shellcheck disable=SC2034 # read by append_benchmark\n"
            '[ -n "${setup_end}" ] || { bench_mode=none; BENCH_EXIT_STATUS=1; }\n'
        ) in script_text
        # Must be set before append_benchmark reads them.
        assert script_text.index("BENCH_EXIT_STATUS=1") < script_text.index(
            "\nappend_benchmark "
        )

    def test_records_compute_node_hostname(self, script_text):
        assert re.search(r'^hostname > "\$\{\w+\}/hostname\.txt"$', script_text, re.M)

    def test_appends_benchmark_before_moving_log(self, script_text):
        append = re.search(r"^append_benchmark ", script_text, re.M)
        first_mv = re.search(r"^mv ", script_text, re.M)
        assert append and first_mv
        assert append.start() < first_mv.start()
        assert re.match(
            r'append_benchmark \S+ "\$\{start_time\}" "\$\{end_time\}" '
            r'"\$\{setup_start\}" "\$\{setup_end\}" "\$\{bench_mode\}"\n',
            script_text[append.start() :],
        )

    def test_payload_stderr_reaches_log(self, script_text):
        assert "2>1|" not in script_text


class TestNerscAthenaJobScripts:
    @pytest.mark.parametrize("script", ATHENA_JOB_SCRIPTS)
    def test_explains_why_pipe_log_is_folded_in(self, script):
        assert (
            "# time -v's report lands in the tee'd pipe, not in the transform's own log,\n"
            "# so the chain folds pipe_file.log into it for append_benchmark to read.\n"
        ) in (REPO / script).read_text()


class TestNerscRunOption:
    def test_has_no_dollar(self, script, script_text):
        # ALRB evaluates `$` in the -r string once, before running any of it.
        option = run_option(script_text)
        for host_value in HOST_EXPANDED_VALUES.get(script, ()):
            option = option.replace(host_value, "")
        assert "$" not in option

    def test_has_no_escaped_quote(self, script_text):
        assert '\\"' not in run_option(script_text)

    def test_records_setup_complete_label_via_date(self, script_text):
        # date prints the label itself so no $(date) is needed in the string.
        assert "date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log" in run_option(
            script_text
        )

    def test_times_payload_with_time_v_after_setup_complete(self, script_text):
        option = run_option(script_text)
        assert "/usr/bin/time -v " in option
        assert option.index("SETUP_COMPLETE") < option.index("/usr/bin/time")


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

    def test_nersc_branch_mounts_global(self):
        # voms-proxy-init reads ~/.globus and the log is moved under $HOME;
        # both live on /global, which the container cannot see unless mounted.
        text = (REPO / "Rucio" / "rucio_script.sh").read_text()
        branch = text.split("\n    nersc)", 1)[1].split(";;", 1)[0]
        assert 'dir_mount="/global:/global"' in branch


class TestFastFramesOutputSize:
    def test_du_reads_histogram_from_config_output_path(self):
        # mc20e_example_config.yml writes histograms to /srv/output/, which is
        # output/ under the CFS directory the script runs from.
        text = (REPO / "NTuple_Hist/fastframes/NERSC/run_fastframes.sh").read_text()
        assert "du output/example_FS.root >> fastframes.log" in text
