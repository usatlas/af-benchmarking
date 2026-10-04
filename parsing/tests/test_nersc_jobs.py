"""Static checks that each NERSC payload script follows the benchmark
conventions: it writes an append_benchmark block before moving its log, and
records the compute node's hostname for the login-node upload step.

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

# Every NERSC job is submitted through sbatch; each payload needs a sub file.
SUB_FILES = {
    "NTuple_Hist/coffea/NERSC/coffea_el9_sub.sh": "NTuple_Hist/coffea/NERSC/run_example.sh",
    "NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_sub.sh": "NTuple_Hist/event_loop/NERSC/columnar/run_eventloop_arrays.sh",
    "NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_sub.sh": "NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh",
}


@pytest.fixture(params=JOB_SCRIPTS)
def script_text(request):
    return (REPO / request.param).read_text()


class TestNerscJobScriptBenchmarkConventions:
    def test_sources_benchmark_utils(self, script_text):
        assert (
            'source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh'
            in script_text
        )

    def test_guards_time_v(self, script_text):
        assert "if [ -x /usr/bin/time ]" in script_text

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


class TestNerscJobsAreSubmittable:
    @pytest.mark.parametrize("sub_file,payload", SUB_FILES.items())
    def test_sub_file_runs_payload(self, sub_file, payload):
        text = (REPO / sub_file).read_text()
        assert "#SBATCH -q regular" in text
        assert f'"$HOME"/AF-Benchmarking/{payload}' in text
