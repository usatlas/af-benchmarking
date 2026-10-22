"""Structure tests for the UC-ODF GitHub Actions workflow.

The workflow cannot be run locally (it needs a self-hosted runner with CVMFS),
so these tests check the invariants that matter here: it stays as close to the
UC workflow as UC-ODF allows, and every script and log it names exists and
matches what ci_parse accepts. Real YAML validation is left to the pre-commit
hooks. PyYAML is not in the test environment, hence the line-based reader.
"""

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ODF_TEXT = (WORKFLOWS / "uc-odf.yml").read_text()
UC_TEXT = (WORKFLOWS / "uchicago.yml").read_text()

# UC has the same jobs plus evnt-native and truth3-native, which cannot run on
# the Ubuntu UC-ODF hosts
ODF_JOBS = [
    "rucio",
    "evnt-el9",
    "evnt-centos7",
    "truth3-el9",
    "truth3-centos7",
    "coffea",
    "eventloop-columnar",
    "eventloop-standard",
    "fastframes",
]
REQUIRED_PARSE_INPUTS = {
    "job",
    "log-file",
    "log-type",
    "cluster",
    "kibana-token",
    "kibana-kind",
    "host",
    "os",
    "mode",
    "containerized",
}
LOG_TYPES = {"rucio", "evnt", "truth3", "coffea", "eventloop", "fastframes"}
NTUPLE_JOBS = ["coffea", "eventloop-columnar", "eventloop-standard", "fastframes"]
# UC steps that UC-ODF deliberately does not have
STEPS_ALLOWED_TO_BE_MISSING = {"fastframes": {"$/.github/actions/setup-globus"}}


def split_jobs(text):
    """Map job name -> the text of that job, from the `jobs:` section."""
    jobs_section = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z0-9-]+):\n", jobs_section, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def split_steps(job_text):
    """List the steps of a job as (label, text); the label is name or uses."""
    chunks = re.split(r"^      - ", job_text, flags=re.MULTILINE)[1:]
    steps = []
    for chunk in chunks:
        match = re.match(r"(?:name: (.+)|uses: (\S+))", chunk)
        steps.append((match.group(1) or match.group(2), chunk))
    return steps


def step_with_inputs(step_text):
    """The `with:` key/value pairs of a step, with quotes removed."""
    block = re.search(r"^        with:\n((?:          .+\n?)+)", step_text, re.M)
    if not block:
        return {}
    pairs = re.findall(r"^          ([a-z-]+): (.+)$", block.group(1), re.M)
    return {key: value.strip().strip('"') for key, value in pairs}


@pytest.fixture(scope="module")
def odf_jobs():
    return split_jobs(ODF_TEXT)


@pytest.fixture(scope="module")
def uc_jobs():
    return split_jobs(UC_TEXT)


def parse_inputs(job_text):
    parse_step = next(
        text
        for _, text in split_steps(job_text)
        if "uses: $/.github/actions/parse" in text
    )
    return step_with_inputs(parse_step)


def execute_command(job_text):
    execute_step = next(
        text for label, text in split_steps(job_text) if label == "execute"
    )
    return re.search(r"run: (.+)", execute_step).group(1).split()


class TestTriggersAndRunner:
    def test_manual_trigger_only(self):
        triggers = ODF_TEXT.split("\njobs:\n", 1)[0].split("\nconcurrency:", 1)[0]
        assert "workflow_dispatch:" in triggers
        for unwanted in ("pull_request:", "schedule:", "push:"):
            assert unwanted not in triggers

    def test_all_jobs_use_the_uc_odf_runner(self, odf_jobs):
        runners = {
            re.search(r"runs-on: (\S+)", text).group(1) for text in odf_jobs.values()
        }
        assert runners == {"arc-runner-set-odf"}

    def test_no_placeholder_note_is_left(self):
        assert "PLACEHOLDER" not in ODF_TEXT

    def test_job_set_is_ucs_minus_the_native_jobs(self, odf_jobs, uc_jobs):
        assert list(odf_jobs) == ODF_JOBS
        assert set(uc_jobs) - set(odf_jobs) == {"evnt-native", "truth3-native"}


class TestParityWithUcWorkflow:
    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_guard_condition_matches_uc(self, job, odf_jobs, uc_jobs):
        def condition(text):
            return re.search(r"^    if:\n(?:      .+\n)+", text, re.M).group(0)

        assert condition(odf_jobs[job]) == condition(uc_jobs[job])

    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_every_uc_step_is_kept_in_order(self, job, odf_jobs, uc_jobs):
        odf_labels = [label for label, _ in split_steps(odf_jobs[job])]
        uc_labels = [
            label
            for label, _ in split_steps(uc_jobs[job])
            if label not in STEPS_ALLOWED_TO_BE_MISSING.get(job, set())
        ]
        remaining = iter(odf_labels)
        # Extra UC-ODF steps are fine; each UC step must still appear, in order
        assert all(label in remaining for label in uc_labels)

    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_parse_inputs_differ_from_uc_only_where_expected(
        self, job, odf_jobs, uc_jobs
    ):
        odf, uc = parse_inputs(odf_jobs[job]), parse_inputs(uc_jobs[job])
        differing = {
            key for key in odf.keys() | uc.keys() if odf.get(key) != uc.get(key)
        }
        # UC runs these natively and reports a different payload file for FastFrames
        allowed = {"cluster", "containerized", "log-file", "payload-file", "os"}
        assert differing <= allowed, differing - allowed
        assert odf["host"] == uc["host"] == "${{ env.NODE_NAME }}"
        assert odf["mode"] == uc["mode"] == "batch"


class TestParseInputs:
    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_parse_inputs_are_complete_and_valid(self, job, odf_jobs):
        inputs = parse_inputs(odf_jobs[job])
        assert REQUIRED_PARSE_INPUTS <= inputs.keys()
        assert inputs["cluster"] == "UC-ODF"
        assert inputs["containerized"] == "true"
        assert inputs["os"] in {"alma9", "centos7"}
        assert inputs["log-type"] in LOG_TYPES
        assert re.fullmatch(r"[a-z0-9_-]+", inputs["job"])

    @pytest.mark.parametrize("job", [j for j in ODF_JOBS if j != "rucio"])
    def test_log_file_is_the_one_the_script_writes(self, job, odf_jobs):
        # Rucio is excluded: its script writes into a timestamped directory and
        # the workflow copies the log to the name checked here
        script = REPO_ROOT / execute_command(odf_jobs[job])[0]
        assert parse_inputs(odf_jobs[job])["log-file"] in script.read_text()


class TestScripts:
    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_script_exists_is_executable_and_is_the_odf_copy(self, job, odf_jobs):
        script = execute_command(odf_jobs[job])[0]
        path = REPO_ROOT / script
        assert path.is_file()
        assert os.access(path, os.X_OK)
        assert "UC-ODF" in script or script == "./Rucio/rucio_script.sh"

    def test_rucio_runs_the_odf_site(self, odf_jobs):
        assert execute_command(odf_jobs["rucio"]) == ["./Rucio/rucio_script.sh", "odf"]

    @pytest.mark.parametrize("job", NTUPLE_JOBS)
    def test_ntuple_jobs_receive_their_directories(self, job, odf_jobs):
        execute_step = next(
            t for label, t in split_steps(odf_jobs[job]) if label == "execute"
        )
        assert "NTUPLE_DIR: ${{ vars.UC_ODF_NTUPLE_DIR }}" in execute_step
        if job == "fastframes":
            assert "FF_DIR: ${{ vars.UC_ODF_FF_DIR }}" in execute_step


class TestNoUcLeftovers:
    def test_no_uc_cluster_or_uc_scripts(self):
        assert "UC-AF" not in ODF_TEXT
        assert "arc-runner-set-uchicago" not in ODF_TEXT
        assert not re.findall(r"\./(?:EVNT|TRUTH3|NTuple_Hist/\w+)/UC/", ODF_TEXT)

    def test_local_actions_exist(self):
        for action in set(re.findall(r"uses: \$/\.github/actions/(\S+)", ODF_TEXT)):
            assert (REPO_ROOT / ".github" / "actions" / action / "action.yml").is_file()
