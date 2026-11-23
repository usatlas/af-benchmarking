"""Tests for the BNL benchmark job scripts (no ATLAS software or HTCondor required)."""

import ast
import json
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
COFFEA_BNL = REPO_ROOT / "NTuple_Hist" / "coffea" / "BNL"
FASTFRAMES_BNL = REPO_ROOT / "NTuple_Hist" / "fastframes" / "BNL"
CONVERSION = REPO_ROOT / "NTuple_Hist" / "rntuple_conversion"
EVENT_LOOP_BNL = REPO_ROOT / "NTuple_Hist" / "event_loop" / "BNL"
CRONTAB_BNL = REPO_ROOT / "CrontabFiles" / "crontab_bnl.txt"
DATASET_DIR_BNL = COFFEA_BNL / "single_campaign_mc20e_dataset_runnable"
RNTUPLE_DATASET_DIR = (
    "/atlasgpfs01/usatlas/data/qlei/"
    "user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS_RNTuple.root"
)


class TestCoffeaPython:
    def test_run_example_sets_up_python_3_13_before_building_the_venv(self):
        # Without an lsetup python, the venv is built from the container's own
        # Python, which differs between sites; every site pins coffea's Python
        # explicitly instead.
        text = (COFFEA_BNL / "run_example.sh").read_text()
        lsetup = re.search(r"lsetup 'python 3\.13\.\d+\S*-x86_64-el9'", text)
        venv = text.find("python3 -m venv venv")
        assert lsetup, "run_example.sh does not lsetup a Python 3.13 build"
        assert venv != -1
        assert lsetup.start() < venv

    def test_run_example_installs_dask_histogram_explicitly(self):
        # coffea 2026.11 made dask-histogram an optional extra; on Python 3.13
        # pip resolves that coffea, so "import hist.dask" in example.py fails
        # unless dask_histogram is requested directly.
        text = (COFFEA_BNL / "run_example.sh").read_text()
        install = re.search(r"pip install [^&\n]*atlas_schema[^&\n]*", text)
        assert install, "run_example.sh has no atlas_schema pip install"
        assert "dask_histogram" in install.group(0)

    def test_run_example_pins_atlas_schema_below_0_5(self):
        # atlas_schema 0.5.0 adds a default photon "mass" on top of the ntuple's
        # own "e" branch, which coffea's Lorentz-vector validation rejects.
        text = (COFFEA_BNL / "run_example.sh").read_text()
        install = re.search(r"pip install [^&\n]*atlas_schema[^&\n]*", text)
        assert install, "run_example.sh has no atlas_schema pip install"
        assert re.search(r"atlas_schema\s*<\s*0\.5", install.group(0))


class TestFastFramesBuild:
    def test_run_fastframes_uses_statanalysis_0_7_3(self):
        # FastFrames 7.2.0 (RNTuple support) is built against StatAnalysis
        # 0.7.3; running it under another release would load a different ROOT
        # than the one the build tree was compiled with.
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert "asetup StatAnalysis,0.7.3" in text
        assert "StatAnalysis,0.6.3" not in text

    def test_run_fastframes_sources_the_0_7_3_build_tree(self):
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert "FastFramesTutorial_0.7.3/TutorialClass/build/setup.sh" in text
        assert "FastFramesTutorial_0.7.3/FastFrames/python/FastFrames.py" in text

    def test_build_script_installs_under_an_explicit_prefix(self):
        # An empty CMAKE_INSTALL_PREFIX installs into the container's /usr.
        text = (FASTFRAMES_BNL / "build_fastframes.sh").read_text()
        assert "asetup StatAnalysis,0.7.3" in text
        assert "-DCMAKE_INSTALL_PREFIX='${FF_DIR}/install'" in text


class TestConversionOutputParent:
    def test_convert_job_defaults_to_the_sibling_dataset_directory(self):
        # UC relies on the output landing next to the input dataset directory.
        text = (CONVERSION / "UC" / "convert_job.sh").read_text()
        assert 'output_parent="${2:-$(dirname "${dataset_dir}")}"' in text

    def test_convert_job_builds_the_output_dir_under_the_output_parent(self):
        text = (CONVERSION / "UC" / "convert_job.sh").read_text()
        assert (
            'output_dir="${output_parent}/$(basename "${dataset_dir%.root}")_RNTuple.root"'
            in text
        )

    def test_bnl_convert_sub_writes_to_a_qlei_owned_directory(self):
        # The input dataset lives under jroblesgo, which qlei cannot write to.
        text = (CONVERSION / "BNL" / "convert.sub").read_text()
        arguments = re.search(r"^arguments\s*=\s*(.+)$", text, re.I | re.M)
        assert arguments, "convert.sub has no arguments line"
        assert "$(input)" in arguments.group(1)
        assert "/atlasgpfs01/usatlas/data/qlei" in arguments.group(1)

    def test_bnl_convert_sub_reads_inputs_from_the_input_list(self):
        text = (CONVERSION / "BNL" / "convert.sub").read_text()
        assert re.search(r"^queue\s+input\s+from\s+inputs\.txt$", text, re.I | re.M)

    def test_bnl_inputs_list_every_ttree_file_of_the_dataset_once(self):
        # The list drives one conversion job per line.
        dataset = (
            "/atlasgpfs01/usatlas/data/jroblesgo/"
            "user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root"
        )
        lines = (CONVERSION / "BNL" / "inputs.txt").read_text().splitlines()
        assert len(lines) == len(set(lines)) == 18
        for line in lines:
            assert re.fullmatch(
                re.escape(dataset)
                + r"/user\.bhodkins\.42165201\._\d{6}\.ANALYSIS\.root",
                line,
            )


class TestCoffeaRNTupleTwin:
    def test_dataset_json_points_every_file_at_the_converted_dataset(self):
        ttree = json.loads((DATASET_DIR_BNL / "af_v2_700402.json").read_text())
        rntuple = json.loads(
            (DATASET_DIR_BNL / "af_v2_700402_rntuple.json").read_text()
        )
        t, r = ttree["Wmunugamma"], rntuple["Wmunugamma"]
        # The conversion keeps every file name, entry count and chunking.
        assert r["metadata"] == t["metadata"]
        assert r["form"] == t["form"]
        t_files = {Path(path).name: info for path, info in t["files"].items()}
        r_files = {Path(path).name: path for path in r["files"]}
        assert set(r_files) == set(t_files)
        for name, path in r_files.items():
            assert path == f"{RNTUPLE_DATASET_DIR}/{name}"
            for key in ("num_entries", "object_path", "steps"):
                assert r["files"][path][key] == t_files[name][key]

    def test_example_selects_the_dataset_by_format(self):
        text = (COFFEA_BNL / "example.py").read_text()
        assert '"--format"' in text
        assert "class VirtualProcessor" in text
        assert re.search(r'"rntuple":\s*.*af_v2_700402_rntuple\.json', text)

    def test_example_keeps_the_ttree_dataset_json_unchanged(self):
        text = (COFFEA_BNL / "example.py").read_text()
        assert re.search(
            r'"ttree":\s*Path\(\s*"/atlasgpfs01/usatlas/data/jroblesgo/'
            r'single_campaign_mc20e_dataset_runnable/af_v2_700402\.json"',
            text,
        )

    def test_run_example_rejects_an_unknown_format(self):
        # The check comes before anything touches the filesystem or ALRB.
        result = subprocess.run(
            ["bash", str(COFFEA_BNL / "run_example.sh"), "parquet"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "unknown format: parquet" in result.stderr

    def test_run_example_gives_each_format_its_own_files(self):
        # Two jobs sharing a venv, split.log and coffea.root would corrupt each
        # other's runs and benchmark logs.
        text = (COFFEA_BNL / "run_example.sh").read_text()
        assert 'format="${1:-ttree}"' in text
        assert 'rntuple) variant_suffix="_rntuple"' in text
        assert 'log_file="coffea_hist${variant_suffix}.log"' in text
        assert (
            'working_dir="/atlasgpfs01/usatlas/data/qlei/ntuple/coffea${variant_suffix}"'
            in text
        )
        assert (
            'output_dir="/atlasgpfs01/usatlas/data/qlei/logs/Coffea_Hist${variant_suffix}/'
            in text
        )
        assert "example.py --format ${format}" in text
        assert "af_v2_700402_rntuple.json" in text

    def test_rntuple_sub_differs_from_the_ttree_sub_only_in_arguments_and_logs(self):
        ttree = (COFFEA_BNL / "coffea_el9.sub").read_text()
        rntuple = (COFFEA_BNL / "coffea_el9_rntuple.sub").read_text()
        expected = ttree.replace("myjob.", "myjob_rntuple.").replace(
            "Queue 1", "Arguments = rntuple\n\nQueue 1"
        )
        assert rntuple == expected

    def test_rntuple_cron_differs_from_the_ttree_cron_only_in_its_identity(self):
        ttree = (COFFEA_BNL / "cron_example.sh").read_text()
        rntuple = (COFFEA_BNL / "cron_example_rntuple.sh").read_text()
        expected = ttree
        for old, new in [
            (
                'log_base="/atlasgpfs01/usatlas/data/qlei/logs/Coffea_Hist"',
                'log_base="/atlasgpfs01/usatlas/data/qlei/logs/Coffea_Hist_rntuple"',
            ),
            ('log_output="coffea_hist.log"', 'log_output="coffea_hist_rntuple.log"'),
            (
                'job_dir="/usatlas/u/qlei/test/coffea"',
                'job_dir="/usatlas/u/qlei/test/coffea_rntuple"',
            ),
            (
                "NTuple_Hist/coffea/BNL/coffea_el9.sub",
                "NTuple_Hist/coffea/BNL/coffea_el9_rntuple.sub",
            ),
            ('pixi_job="coffea"', 'pixi_job="coffea-rntuple"'),
        ]:
            assert old in expected
            expected = expected.replace(old, new)
        assert rntuple == expected

    def test_crontab_runs_the_rntuple_twin_at_a_different_minute(self):
        # Same-minute starts would make the two formats compete for the same
        # GPFS and CPUs, so the benchmark would measure the contention.
        entries = {
            name: re.search(
                rf"^(\S+)\s+\*/6 \* \* \*\s+\S*/coffea/BNL/{name}\.sh$",
                CRONTAB_BNL.read_text(),
                re.M,
            )
            for name in ("cron_example", "cron_example_rntuple")
        }
        assert all(entries.values())
        assert entries["cron_example"].group(1) != entries[
            "cron_example_rntuple"
        ].group(1)


class TestEventLoopStatAnalysis:
    @pytest.mark.parametrize(
        "script",
        ["columnar/run_eventloop_arrays.sh", "standard/run_eventloop_noarrays.sh"],
    )
    def test_run_script_uses_statanalysis_0_7_3(self, script):
        # The RNTuple twins read their data with ROOT 6.38 from StatAnalysis
        # 0.7.3, so the TTree jobs move with them to keep the pair comparable.
        text = (EVENT_LOOP_BNL / script).read_text()
        assert "asetup StatAnalysis,0.7.3" in text
        assert "StatAnalysis,0.6.3" not in text

    @pytest.mark.parametrize(
        "payload", ["columnar/eventloop_arrays.py", "standard/eventloop_noarrays.py"]
    )
    def test_payload_avoids_datetime_utc_missing_from_python_3_10(self, payload):
        # StatAnalysis 0.7.3 bundles Python 3.10, where datetime.UTC (3.11+) does
        # not exist; importing it kills the job before it reads an event.
        tree = ast.parse((EVENT_LOOP_BNL / payload).read_text())
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "datetime"
            for alias in node.names
        }
        names_used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert "UTC" not in imported
        assert "UTC" not in names_used
