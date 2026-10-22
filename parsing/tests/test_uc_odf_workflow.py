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

# The same jobs, in the same order, as uchicago.yml. The runner image is
# AlmaLinux 9, so the native jobs run there as they do at UC.
ODF_JOBS = [
    "rucio",
    "evnt-native",
    "evnt-el9",
    "evnt-centos7",
    "truth3-native",
    "truth3-el9",
    "truth3-centos7",
    "coffea",
    "eventloop-columnar",
    "eventloop-standard",
    "fastframes",
]
# Scripts the UC-ODF workflow runs that are not UC-ODF copies
SHARED_SCRIPTS = {
    "./Rucio/rucio_script.sh",
    "./EVNT/UC/Native/run_evnt_native_batch.sh",
    "./TRUTH3/UC/Native/run_truth3_native_batch.sh",
}
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
        steps.append(
            (match.group(1) or match.group(2), without_trailing_comments(chunk))
        )
    return steps


def without_trailing_comments(step_text):
    """Drop the blank and comment lines after a step: they belong to the next."""
    lines = step_text.split("\n")
    while lines and (not lines[-1].strip() or lines[-1].startswith("      #")):
        lines.pop()
    return "\n".join(lines) + "\n"


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
    def test_triggers_are_ucs_and_nothing_else(self):
        # Pull requests also test the workflow before it is on main, and their
        # runs skip the Kibana upload
        triggers = ODF_TEXT.split("\njobs:\n", 1)[0].split("\nconcurrency:", 1)[0]
        names = set(re.findall(r"^  ([a-z_]+):", triggers, re.M))
        assert names == {"pull_request", "schedule", "workflow_dispatch"}

    @pytest.mark.parametrize("trigger", ["pull_request", "schedule"])
    def test_trigger_is_identical_to_uc(self, trigger):
        def block(text):
            return re.search(rf"^  {trigger}:\n(?:    .+\n)+", text, re.M).group(0)

        assert block(ODF_TEXT) == block(UC_TEXT)

    def test_schedule_runs_every_six_hours(self):
        assert '    - cron: "0 */6 * * *"\n' in ODF_TEXT

    def test_all_jobs_use_the_uc_odf_runner(self, odf_jobs):
        runners = {
            re.search(r"runs-on: (\S+)", text).group(1) for text in odf_jobs.values()
        }
        assert runners == {"arc-runner-set-odf"}

    def test_no_placeholder_note_is_left(self):
        assert "PLACEHOLDER" not in ODF_TEXT

    def test_job_set_is_the_same_as_ucs(self, odf_jobs, uc_jobs):
        assert list(odf_jobs) == ODF_JOBS
        assert list(odf_jobs) == list(uc_jobs)


class TestParityWithUcWorkflow:
    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_guard_condition_matches_uc(self, job, odf_jobs, uc_jobs):
        def condition(text):
            return re.search(r"^    if:\n(?:      .+\n)+", text, re.M).group(0)

        assert condition(odf_jobs[job]) == condition(uc_jobs[job])

    @pytest.mark.parametrize("job", ODF_JOBS)
    def test_export_node_name_step_is_identical_to_uc(self, job, odf_jobs, uc_jobs):
        # The UC-ODF runner sets NODE_NAME from the node name, like UC's runner
        def export_step(text):
            return next(
                step for label, step in split_steps(text) if label == "Export node name"
            )

        assert export_step(odf_jobs[job]) == export_step(uc_jobs[job])

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
        # Only the native jobs run outside a container
        assert inputs["containerized"] == (
            "false" if job.endswith("-native") else "true"
        )
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
        assert "UC-ODF" in script or script in SHARED_SCRIPTS

    def test_rucio_runs_the_odf_site(self, odf_jobs):
        assert execute_command(odf_jobs["rucio"]) == ["./Rucio/rucio_script.sh", "odf"]


class TestDataDirectories:
    # The runner mounts a persistent volume at /data/af-benchmarking, which is
    # where the ntuples are staged and FastFrames is built
    HEADER = ODF_TEXT.split("\njobs:\n", 1)[0]

    def test_directories_are_set_once_for_the_whole_workflow(self):
        assert "\nenv:\n" in self.HEADER
        ntuple_dir = (
            "/data/af-benchmarking/"
            "user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root"
        )
        assert f"  NTUPLE_DIR: {ntuple_dir}\n" in self.HEADER
        assert "  FF_DIR: /data/af-benchmarking/FastFramesTutorial\n" in self.HEADER

    def test_jobs_do_not_override_them(self, odf_jobs):
        for text in odf_jobs.values():
            assert "NTUPLE_DIR" not in text
            assert "FF_DIR" not in text

    def test_no_repository_variables_are_needed(self):
        assert "vars." not in ODF_TEXT


class TestFastframesIsPrebuilt:
    # FastFrames is built once, by an administrator, in FF_DIR on the runner
    # volume. The workflow only runs it.
    def test_no_job_builds_anything(self):
        code = "\n".join(
            line for line in ODF_TEXT.splitlines() if not line.lstrip().startswith("#")
        )
        assert "cmake" not in code
        assert "git clone" not in code

    def test_fastframes_job_has_no_build_step(self, odf_jobs):
        labels = [label for label, _ in split_steps(odf_jobs["fastframes"])]
        assert "build FastFrames" not in labels
        assert "execute" in labels


class TestNativeJobsAreUcs:
    # The native scripts use only relative paths and CVMFS, so the UC ones run
    # unchanged on the AlmaLinux 9 runner: no UC-ODF copy is needed
    @pytest.mark.parametrize("job", ["evnt-native", "truth3-native"])
    def test_job_is_ucs_apart_from_runner_and_cluster(self, job, odf_jobs, uc_jobs):
        def normalised(text):
            return (
                text.replace("arc-runner-set-uchicago", "RUNNER")
                .replace("arc-runner-set-odf", "RUNNER")
                .replace("UC-AF", "CLUSTER")
                .replace("UC-ODF", "CLUSTER")
            )

        assert normalised(odf_jobs[job]) == normalised(uc_jobs[job])

    @pytest.mark.parametrize("job", ["evnt-native", "truth3-native"])
    def test_job_runs_ucs_native_script_and_is_not_containerized(self, job, odf_jobs):
        assert execute_command(odf_jobs[job])[0] in SHARED_SCRIPTS
        assert parse_inputs(odf_jobs[job])["containerized"] == "false"


class TestNoUcLeftovers:
    def test_no_uc_cluster_or_uc_scripts(self):
        assert "UC-AF" not in ODF_TEXT
        assert "arc-runner-set-uchicago" not in ODF_TEXT
        uc_scripts = set(
            re.findall(r"\./(?:EVNT|TRUTH3|NTuple_Hist/\w+)/UC/\S+", ODF_TEXT)
        )
        # Only the native scripts are shared with UC
        assert uc_scripts <= SHARED_SCRIPTS

    def test_local_actions_exist(self):
        for action in set(re.findall(r"uses: \$/\.github/actions/(\S+)", ODF_TEXT)):
            assert (REPO_ROOT / ".github" / "actions" / action / "action.yml").is_file()
