"""Tests for the per-site benchmark shell scripts (no ATLAS software required)."""

import importlib.util
import json
import os
import py_compile
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COFFEA_ODF_DIR = REPO_ROOT / "NTuple_Hist" / "coffea" / "UC-ODF"
DATASET_JSON = (
    REPO_ROOT
    / "NTuple_Hist"
    / "coffea"
    / "single_campaign_mc20e_dataset_runnable"
    / "af_v2_700402.json"
)

NTUPLE_SCRIPTS = [
    "NTuple_Hist/event_loop/UC-ODF/columnar/run_eventloop_arrays.sh",
    "NTuple_Hist/event_loop/UC-ODF/standard/run_eventloop_noarrays.sh",
    "NTuple_Hist/coffea/UC-ODF/run_example.sh",
]
NTUPLE_PYTHON = [
    "NTuple_Hist/event_loop/UC-ODF/columnar/event_loop_arrays.py",
    "NTuple_Hist/event_loop/UC-ODF/standard/event_loop_noarrays.py",
    "NTuple_Hist/coffea/UC-ODF/example.py",
    "NTuple_Hist/coffea/UC-ODF/fileset_paths.py",
]


class TestRucioScriptOdfSite:
    def test_odf_is_a_known_site(self, tmp_path):
        # HOME points at an empty temp dir so container_el9 fails at its first
        # `cd` into $HOME/af_benchmarking/rucio/ and never reaches setupATLAS or
        # the download. The test only checks the site dispatch.
        result = subprocess.run(
            ["bash", "Rucio/rucio_script.sh", "odf"],
            cwd=REPO_ROOT,
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout + result.stderr
        assert "Running for site: odf" in output
        assert "Unknown site" not in output


class TestUcOdfEvntScripts:
    @pytest.mark.parametrize(
        "script",
        [
            "EVNT/UC-ODF/EL9_i/run_evnt_el9_interactive.sh",
            "EVNT/UC-ODF/CentOS7_i/run_evnt_centos7_interactive.sh",
        ],
    )
    def test_script_is_executable_and_valid_bash(self, script):
        path = REPO_ROOT / script
        assert path.is_file()
        assert os.access(path, os.X_OK)
        # -n parses the script without running it
        subprocess.run(["bash", "-n", str(path)], check=True)


class TestUcOdfNtupleScripts:
    @pytest.mark.parametrize("script", NTUPLE_SCRIPTS)
    def test_script_is_executable_and_valid_bash(self, script):
        path = REPO_ROOT / script
        assert path.is_file()
        assert os.access(path, os.X_OK)
        subprocess.run(["bash", "-n", str(path)], check=True)

    @pytest.mark.parametrize("script", NTUPLE_SCRIPTS)
    def test_script_requires_ntuple_dir(self, script):
        # The scripts must stop at the NTUPLE_DIR check, before any ATLAS setup
        env = {k: v for k, v in os.environ.items() if k != "NTUPLE_DIR"}
        result = subprocess.run(
            ["bash", script],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert "NTUPLE_DIR" in result.stdout + result.stderr

    @pytest.mark.parametrize("path", NTUPLE_SCRIPTS + NTUPLE_PYTHON)
    def test_no_uc_specific_paths(self, path):
        text = (REPO_ROOT / path).read_text()
        # /data/kratsg is UC's ntuple area; /home/runner is the GitHub runner checkout
        assert "/data/kratsg" not in text
        assert "/home/runner" not in text

    @pytest.mark.parametrize("path", NTUPLE_PYTHON)
    def test_python_file_compiles(self, path, tmp_path):
        py_compile.compile(
            str(REPO_ROOT / path), cfile=str(tmp_path / "out.pyc"), doraise=True
        )


class TestRelocateFileset:
    @pytest.fixture
    def module(self):
        spec = importlib.util.spec_from_file_location(
            "fileset_paths", COFFEA_ODF_DIR / "fileset_paths.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @pytest.fixture
    def dataset(self):
        return json.loads(DATASET_JSON.read_text())["Wmunugamma"]

    def test_files_move_under_ntuple_dir_keeping_names(self, module, dataset, tmp_path):
        relocated = module.relocate_fileset(dataset, tmp_path)
        assert len(relocated["files"]) == 18
        assert all(Path(p).parent == tmp_path for p in relocated["files"])
        assert sorted(Path(p).name for p in relocated["files"]) == sorted(
            Path(p).name for p in dataset["files"]
        )

    def test_per_file_and_dataset_metadata_are_preserved(
        self, module, dataset, tmp_path
    ):
        relocated = module.relocate_fileset(dataset, tmp_path)
        assert relocated["metadata"] == dataset["metadata"]
        assert relocated["form"] == dataset["form"]
        for old_path, new_path in zip(dataset["files"], relocated["files"]):
            assert relocated["files"][new_path] == dataset["files"][old_path]

    def test_input_is_not_modified(self, module, dataset, tmp_path):
        before = json.dumps(dataset, sort_keys=True)
        module.relocate_fileset(dataset, tmp_path)
        assert json.dumps(dataset, sort_keys=True) == before

    def test_duplicate_file_names_raise(self, module, tmp_path):
        # Two source files with the same name would collapse into one entry
        dataset = {"files": {"/a/x.root": {}, "/b/x.root": {}}, "metadata": {}}
        with pytest.raises(ValueError, match=r"x\.root"):
            module.relocate_fileset(dataset, tmp_path)
