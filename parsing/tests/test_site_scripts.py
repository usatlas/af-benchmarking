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


FASTFRAMES_DIR = REPO_ROOT / "NTuple_Hist" / "fastframes"
FASTFRAMES_ODF_DIR = FASTFRAMES_DIR / "UC-ODF"
UC_FILELIST = FASTFRAMES_DIR / "UC" / "mc20e_filelist.txt"
# Config keys that hold paths and so legitimately differ between sites
CONFIG_PATH_KEYS = (
    "input_filelist_path",
    "input_sumweights_path",
    "output_path_histograms",
)


class TestUcOdfFastFramesRun:
    SCRIPT = "NTuple_Hist/fastframes/UC-ODF/run_fastframes.sh"
    MAKE_FILELIST = "NTuple_Hist/fastframes/UC-ODF/make_filelist.sh"

    @pytest.mark.parametrize("script", [SCRIPT, MAKE_FILELIST])
    def test_script_is_executable_and_valid_bash(self, script):
        path = REPO_ROOT / script
        assert path.is_file()
        assert os.access(path, os.X_OK)
        subprocess.run(["bash", "-n", str(path)], check=True)

    @pytest.mark.parametrize(
        ("has_ntuple_dir", "missing"),
        [
            (False, "NTUPLE_DIR"),
            (True, "FF_DIR"),
        ],
    )
    def test_run_script_requires_its_directories(
        self, has_ntuple_dir, missing, tmp_path
    ):
        # Must stop at the check, before any ATLAS setup
        (tmp_path / "ntuple.root").touch()
        env_vars = {"NTUPLE_DIR": str(tmp_path)} if has_ntuple_dir else {}
        env = {k: v for k, v in os.environ.items() if k not in ("NTUPLE_DIR", "FF_DIR")}
        result = subprocess.run(
            ["bash", self.SCRIPT],
            cwd=REPO_ROOT,
            env={**env, **env_vars},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert missing in result.stdout + result.stderr

    def test_run_script_stops_if_fastframes_is_not_built(self, tmp_path):
        # Otherwise the missing build only shows up deep inside the container
        ntuples = tmp_path / "ntuples"
        ntuples.mkdir()
        (ntuples / "ntuple.root").touch()
        empty_ff_dir = tmp_path / "ff"
        empty_ff_dir.mkdir()

        result = run_with_env(
            ["bash", self.SCRIPT],
            {"NTUPLE_DIR": str(ntuples), "FF_DIR": str(empty_ff_dir)},
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "FastFrames is not built" in output
        assert str(empty_ff_dir) in output
        # The build recipe is not part of this repository any more
        assert "build_fastframes.sh" not in output

    def test_make_filelist_reproduces_uc_list_for_a_local_directory(self, tmp_path):
        uc_lines = UC_FILELIST.read_text().splitlines()
        for line in uc_lines:
            (tmp_path / Path(line.rsplit(" ", 1)[1]).name).touch()
        # Unrelated files must not leak into the list
        (tmp_path / "notes.txt").touch()

        result = subprocess.run(
            ["bash", self.MAKE_FILELIST, str(tmp_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        expected = [
            f"{line.rsplit(' ', 1)[0]} {tmp_path / Path(line.rsplit(' ', 1)[1]).name}"
            for line in uc_lines
        ]
        assert result.stdout.splitlines() == expected

    def test_make_filelist_fails_on_directory_without_ntuples(self, tmp_path):
        result = subprocess.run(
            ["bash", self.MAKE_FILELIST, str(tmp_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert "no .root files" in result.stdout + result.stderr

    def test_config_differs_from_uc_only_in_path_keys(self):
        def without_path_keys(path):
            # Comments are ignored: only the settings must not drift
            return [
                line
                for line in path.read_text().splitlines()
                if not line.strip().startswith("#")
                and line.strip().split(":")[0] not in CONFIG_PATH_KEYS
            ]

        assert without_path_keys(
            FASTFRAMES_ODF_DIR / "mc20e_example_config.yml"
        ) == without_path_keys(FASTFRAMES_DIR / "UC" / "mc20e_example_config.yml")

    def test_config_inputs_resolve_inside_the_repo(self):
        text = (FASTFRAMES_ODF_DIR / "mc20e_example_config.yml").read_text()
        sumweights = next(
            line.split('"')[1]
            for line in text.splitlines()
            if line.strip().startswith("input_sumweights_path")
        )
        assert (REPO_ROOT / sumweights).is_file()

    @pytest.mark.parametrize(
        "name", ["run_fastframes.sh", "make_filelist.sh", "mc20e_example_config.yml"]
    )
    def test_no_uc_specific_paths(self, name):
        text = (FASTFRAMES_ODF_DIR / name).read_text()
        for uc_path in ("/data/kratsg", "/data/selbor", "/home/selbor"):
            assert uc_path not in text


NTUPLE_UTILS = "NTuple_Hist/UC-ODF/ntuple_utils.sh"
NTUPLE_RUN_SCRIPTS = NTUPLE_SCRIPTS + [
    "NTuple_Hist/fastframes/UC-ODF/run_fastframes.sh"
]


def run_with_env(command, env_vars):
    env = {k: v for k, v in os.environ.items() if k not in ("NTUPLE_DIR", "FF_DIR")}
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env={**env, **env_vars},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


class TestRequireNtupleDir:
    @staticmethod
    def check(env_vars):
        return run_with_env(
            ["bash", "-c", f"source ./{NTUPLE_UTILS}; require_ntuple_dir"], env_vars
        )

    def test_accepts_absolute_dir_with_root_files(self, tmp_path):
        (tmp_path / "ntuple.root").touch()
        assert self.check({"NTUPLE_DIR": str(tmp_path)}).returncode == 0

    def test_rejects_unset_variable(self):
        result = self.check({})
        assert result.returncode != 0
        assert "NTUPLE_DIR" in result.stdout + result.stderr

    def test_rejects_relative_path(self, tmp_path):
        # A relative path would not resolve the same way inside the container
        (tmp_path / "ntuple.root").touch()
        result = self.check({"NTUPLE_DIR": "relative/ntuples"})
        assert result.returncode != 0
        assert "absolute" in result.stdout + result.stderr

    @pytest.mark.parametrize("other_file", [None, "notes.txt"])
    def test_rejects_directory_without_root_files(self, tmp_path, other_file):
        if other_file:
            (tmp_path / other_file).touch()
        result = self.check({"NTUPLE_DIR": str(tmp_path)})
        assert result.returncode != 0
        assert "No .root files" in result.stdout + result.stderr

    @pytest.mark.parametrize("script", NTUPLE_RUN_SCRIPTS)
    def test_run_scripts_stop_on_an_empty_ntuple_dir(self, script, tmp_path):
        # FF_DIR is set so that only the ntuple check can be the reason to stop
        result = run_with_env(
            ["bash", script],
            {"NTUPLE_DIR": str(tmp_path), "FF_DIR": str(tmp_path)},
        )
        assert result.returncode != 0
        assert "No .root files" in result.stdout + result.stderr

    @pytest.mark.parametrize("script", NTUPLE_RUN_SCRIPTS)
    def test_run_scripts_stop_on_a_relative_ntuple_dir(self, script, tmp_path):
        result = run_with_env(
            ["bash", script],
            {"NTUPLE_DIR": "relative/ntuples", "FF_DIR": str(tmp_path)},
        )
        assert result.returncode != 0
        assert "absolute" in result.stdout + result.stderr
