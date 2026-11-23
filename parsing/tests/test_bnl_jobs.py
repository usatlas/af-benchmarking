"""Tests for the BNL benchmark job scripts (no ATLAS software or HTCondor required)."""

import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

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


def cron_schedule(script):
    """The five schedule fields of the crontab line that runs ``script``."""
    match = re.search(
        rf"^(\S+\s+\S+\s+\S+\s+\S+\s+\S+)\s+\S*/{re.escape(script)}$",
        CRONTAB_BNL.read_text(),
        re.M,
    )
    assert match, f"{script} is not in the crontab"
    return match.group(1)


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

    def test_run_example_records_setup_complete_without_a_runtime_dollar(self):
        # ALRB expands a \\$ inside the -r string once, before any command runs,
        # so \\$(date) recorded the start of setup as its end (about 1 s instead
        # of the ~40 s a fresh venv takes). date prints the label itself instead.
        text = (COFFEA_BNL / "run_example.sh").read_text()
        assert "\\$(" not in text
        assert "date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log" in text

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

    def test_example_routes_each_format_to_its_dataset_and_runner(self):
        # Importing example.py needs coffea, dask and ATLAS packages, so check
        # the routing in the source: the dataset is chosen by --format, and only
        # rntuple goes through the virtual-array runner.
        text = (COFFEA_BNL / "example.py").read_text()
        assert "DATASET_JSONS[args.format].read_text()" in text
        assert re.search(
            r'if args\.format == "rntuple":\s+'
            r"computed, start_time_utc, start_time = run_virtual\(",
            text,
        )
        assert re.search(
            r"else:\s+computed, start_time_utc, start_time = run_dask\(", text
        )

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

    def test_crontab_runs_the_rntuple_twin_on_the_same_schedule(self):
        # The pair is only comparable if both formats run under the same load.
        # Staggering them put one on the busy :00 slot and the other on a quiet
        # one, and the slower TTree jobs outlast any offset anyway.
        assert cron_schedule("coffea/BNL/cron_example.sh") == cron_schedule(
            "coffea/BNL/cron_example_rntuple.sh"
        )


EVENT_LOOP_TWINS = {
    "columnar": {
        "payload": EVENT_LOOP_BNL / "columnar" / "eventloop_arrays.py",
        "run": EVENT_LOOP_BNL / "columnar" / "run_eventloop_arrays.sh",
        "sub": "eventloop_arrays.sub",
        "cron": "cron_eventloop_arrays.sh",
        "stem": "eventloop_arrays",
        "job": "eventloop-columnar",
        "sub_prefix": "eventloop_arrays.",
    },
    "standard": {
        "payload": EVENT_LOOP_BNL / "standard" / "eventloop_noarrays.py",
        "run": EVENT_LOOP_BNL / "standard" / "run_eventloop_noarrays.sh",
        "sub": "eventloop_noarrays.sub",
        "cron": "cron_eventloop_noarrays.sh",
        "stem": "eventloop_noarrays",
        "job": "eventloop-standard",
        "sub_prefix": "myjob.",
    },
}


class FakeEntry:
    """The part of ROOT 6.38's REntry pythonization the payloads rely on."""

    def __init__(self):
        self.values = {}
        self.token_requests = []
        self.key_kinds = []

    def GetToken(self, name):
        self.token_requests.append(name)
        return ("token", name)

    def __getitem__(self, key):
        self.key_kinds.append("token" if isinstance(key, tuple) else "name")
        name = key[1] if isinstance(key, tuple) else key
        return self.values[name]


class FakeReader:
    """The part of ROOT 6.38's RNTupleReader the payloads rely on."""

    def __init__(self, events):
        self.events = events
        self.entry = FakeEntry()

    def CreateEntry(self):
        return self.entry

    def GetNEntries(self):
        return len(self.events)

    def LoadEntry(self, index, entry):
        # 6.38 refuses LoadEntry without an explicit entry made by the reader.
        assert entry is self.entry
        entry.values = self.events[index]


class FakeHistogram:
    def __init__(self):
        self.fills = []

    def Fill(self, x, weight):
        self.fills.append((x, weight))


def load_payload(monkeypatch, path):
    # The payloads import ROOT at module level; stub it so no ATLAS software is needed.
    root = MagicMock()
    monkeypatch.setitem(sys.modules, "ROOT", root)
    spec = importlib.util.spec_from_file_location(f"bnl_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, root


def event(pts, tight, weight_mc, weight_pileup):
    return {
        "ph_pt_NOSYS": pts,
        "ph_select_tightID_NOSYS": [chr(flag) for flag in tight],
        "weight_mc_NOSYS": weight_mc,
        "weight_pileup_NOSYS": weight_pileup,
    }


# Gives the normalization xs * genFiltEff * kfactor * luminosity / sum_of_weights = 0.5.
EVENT_LOOP_METADATA = {
    "xs": 2.0,
    "luminosity": 1.0,
    "genFiltEff": 1.0,
    "sum_of_weights": 4.0,
    "kfactor": 1.0,
}


@pytest.mark.parametrize("twin", EVENT_LOOP_TWINS)
class TestEventLoopRNTuple:
    def test_loop_fills_the_first_tight_photon_of_each_event(self, monkeypatch, twin):
        module, root = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        reader = FakeReader(
            [
                event([30000.0, 50000.0, 70000.0], [0, 1, 1], 2.0, 0.5),
                event([], [], 1.0, 1.0),
                event([10000.0, 20000.0], [0, 0], 1.0, 1.0),
                event([40000.0], [1], 1.5, 1.0),
            ]
        )
        root.RNTupleReader.Open.return_value = reader
        histogram = FakeHistogram()

        processed = module.photon_eventloop_rntuple(
            "f.root", histogram, EVENT_LOOP_METADATA
        )

        assert processed == 4
        assert histogram.fills == [
            (pytest.approx(50.0), pytest.approx(0.5 * 2.0 * 0.5)),
            (pytest.approx(40.0), pytest.approx(0.5 * 1.5 * 1.0)),
        ]

    def test_loop_opens_the_file_with_the_root_6_38_reader(self, monkeypatch, twin):
        # RNTuple left ROOT::Experimental in ROOT 6.36; StatAnalysis 0.7.3 has 6.38.
        module, root = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        root.RNTupleReader.Open.return_value = FakeReader([])

        module.photon_eventloop_rntuple("f.root", FakeHistogram(), EVENT_LOOP_METADATA)

        root.RNTupleReader.Open.assert_called_once_with("analysis", "f.root")
        root.Experimental.RNTupleReader.Open.assert_not_called()

    def test_formats_dispatch_to_their_own_loop_and_dataset(self, monkeypatch, twin):
        module, _ = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        assert module.EVENTLOOPS == {
            "ttree": module.photon_eventloop,
            "rntuple": module.photon_eventloop_rntuple,
        }
        # The TTree dataset stays where it was; its owner is another user.
        assert module.DATASET_PATHS == {
            "ttree": "/atlasgpfs01/usatlas/data/jroblesgo/"
            "user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/",
            "rntuple": RNTUPLE_DATASET_DIR + "/",
        }

    def test_loop_reads_fields_the_way_its_twin_is_defined(self, monkeypatch, twin):
        # Columnar resolves each field's token once; standard looks the name up
        # on every event. Without this the two twins could silently converge.
        module, root = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        reader = FakeReader([event([10000.0], [1], 1.0, 1.0)] * 5)
        root.RNTupleReader.Open.return_value = reader

        module.photon_eventloop_rntuple("f.root", FakeHistogram(), EVENT_LOOP_METADATA)

        entry = reader.entry
        if twin == "columnar":
            assert len(entry.token_requests) == 4
            assert set(entry.key_kinds) == {"token"}
        else:
            assert entry.token_requests == []
            assert set(entry.key_kinds) == {"name"}

    @staticmethod
    def make_dataset(tmp_path, name, n_files):
        directory = tmp_path / name
        directory.mkdir()
        for index in range(n_files):
            (directory / f"f{index}.root").touch()
        return directory

    @pytest.mark.parametrize("fmt", ["ttree", "rntuple"])
    def test_main_routes_each_format_to_its_loop_and_dataset(
        self, monkeypatch, tmp_path, twin, fmt
    ):
        # A routing slip (rntuple benchmarking the TTree files, or the reverse)
        # would still "succeed", so check which loop gets which files.
        module, _ = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        datasets = {
            "ttree": self.make_dataset(tmp_path, "ttree", 2),
            "rntuple": self.make_dataset(tmp_path, "rntuple", 3),
        }
        calls = []

        def recorder(label):
            def loop(f_name, histogram, metadata):
                calls.append((label, f_name))
                return 10

            return loop

        monkeypatch.setattr(
            module, "DATASET_PATHS", {k: f"{v}/" for k, v in datasets.items()}
        )
        monkeypatch.setattr(
            module,
            "EVENTLOOPS",
            {"ttree": recorder("ttree"), "rntuple": recorder("rntuple")},
        )
        monkeypatch.setattr(sys, "argv", ["payload", "--format", fmt])

        module.main()

        assert calls == [
            (fmt, str(path)) for path in sorted(datasets[fmt].glob("*.root"))
        ]

    @pytest.mark.parametrize("state", ["missing", "empty"])
    def test_main_fails_when_the_dataset_yields_no_events(
        self, monkeypatch, tmp_path, twin, state
    ):
        # A zero-event run used to exit 0 and upload as a fast success.
        module, _ = load_payload(monkeypatch, EVENT_LOOP_TWINS[twin]["payload"])
        dataset = tmp_path / "dataset"
        if state == "empty":
            dataset.mkdir()
        monkeypatch.setattr(
            module, "DATASET_PATHS", {"ttree": f"{dataset}/", "rntuple": f"{dataset}/"}
        )
        monkeypatch.setattr(sys, "argv", ["payload", "--format", "rntuple"])

        with pytest.raises(SystemExit) as raised:
            module.main()

        assert raised.value.code not in (0, None)

    def test_main_takes_a_format_option(self, twin):
        text = EVENT_LOOP_TWINS[twin]["payload"].read_text()
        assert 'parser.add_argument("--format", choices=sorted(EVENTLOOPS)' in text

    def test_run_script_rejects_an_unknown_format(self, twin):
        # The check comes before anything touches the filesystem or ATLAS setup.
        result = subprocess.run(
            ["bash", str(EVENT_LOOP_TWINS[twin]["run"]), "parquet"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "unknown format: parquet" in result.stderr

    def test_run_script_gives_each_format_its_own_files(self, twin):
        # Both formats' jobs used to run in the repo checkout and share split.log
        # and the output histogram; overlapping runs then clobbered each other.
        stem = EVENT_LOOP_TWINS[twin]["stem"]
        text = EVENT_LOOP_TWINS[twin]["run"].read_text()
        assert 'format="${1:-ttree}"' in text
        assert 'rntuple) variant_suffix="_rntuple"' in text
        assert f'log_file="{stem}${{variant_suffix}}.log"' in text
        assert (
            f'working_dir="/atlasgpfs01/usatlas/data/qlei/ntuple/{stem}${{variant_suffix}}"'
            in text
        )
        assert (
            f'output_dir="/atlasgpfs01/usatlas/data/qlei/logs/{stem}${{variant_suffix}}/'
            in text
        )
        assert re.search(rf'{stem}\.py --format "?\$\{{format\}}"?', text)

    def test_rntuple_sub_differs_from_the_ttree_sub_only_in_arguments_and_logs(
        self, twin
    ):
        info = EVENT_LOOP_TWINS[twin]
        directory = info["payload"].parent
        ttree = (directory / info["sub"]).read_text()
        rntuple = (directory / info["sub"].replace(".sub", "_rntuple.sub")).read_text()
        prefix = info["sub_prefix"]
        expected = ttree.replace(
            f"{prefix}$(", prefix.replace(".", "_rntuple.") + "$("
        ).replace("Queue 1", "Arguments = rntuple\n\nQueue 1")
        assert rntuple == expected

    def test_rntuple_cron_differs_from_the_ttree_cron_only_in_its_identity(self, twin):
        info = EVENT_LOOP_TWINS[twin]
        directory = info["payload"].parent
        stem = info["stem"]
        ttree = (directory / info["cron"]).read_text()
        rntuple = (directory / info["cron"].replace(".sh", "_rntuple.sh")).read_text()
        expected = ttree
        for old, new in [
            (
                f'log_base="/atlasgpfs01/usatlas/data/qlei/logs/{stem}"',
                f'log_base="/atlasgpfs01/usatlas/data/qlei/logs/{stem}_rntuple"',
            ),
            (f'log_output="{stem}.log"', f'log_output="{stem}_rntuple.log"'),
            (
                f'job_dir="/usatlas/u/qlei/test/{stem}"',
                f'job_dir="/usatlas/u/qlei/test/{stem}_rntuple"',
            ),
            (f"/{info['sub']}", f"/{info['sub'].replace('.sub', '_rntuple.sub')}"),
            (f'pixi_job="{info["job"]}"', f'pixi_job="{info["job"]}-rntuple"'),
        ]:
            assert old in expected
            expected = expected.replace(old, new)
        assert rntuple == expected

    def test_crontab_runs_the_rntuple_twin_on_the_same_schedule(self, twin):
        # See the matching coffea test: the pair must run under the same load.
        script = f"event_loop/BNL/{twin}/{EVENT_LOOP_TWINS[twin]['cron']}"
        assert cron_schedule(script) == cron_schedule(
            script.replace(".sh", "_rntuple.sh")
        )


class TestFastFramesRNTupleTwin:
    def test_filelist_points_every_entry_at_the_converted_dataset(self):
        ttree = (FASTFRAMES_BNL / "mc20e_filelist.txt").read_text().splitlines()
        rntuple = (
            (FASTFRAMES_BNL / "mc20e_filelist_rntuple.txt").read_text().splitlines()
        )
        assert len(rntuple) == len(ttree) == 18
        for t_line, r_line in zip(ttree, rntuple):
            *t_columns, t_path = t_line.split()
            *r_columns, r_path = r_line.split()
            assert r_columns == t_columns
            assert r_path == f"{RNTUPLE_DATASET_DIR}/{Path(t_path).name}"

    def test_config_differs_from_the_ttree_config_only_in_the_filelist(self):
        ttree = (FASTFRAMES_BNL / "mc20e_example_config.yml").read_text()
        rntuple = (FASTFRAMES_BNL / "mc20e_example_config_rntuple.yml").read_text()
        old = 'input_filelist_path: "/srv/input/mc20e_filelist.txt"'
        assert ttree.count(old) == 1
        assert rntuple == ttree.replace(
            old, 'input_filelist_path: "/srv/input/mc20e_filelist_rntuple.txt"'
        )

    def test_run_script_rejects_an_unknown_format(self):
        # The check comes before anything touches the filesystem or ATLAS setup.
        result = subprocess.run(
            ["bash", str(FASTFRAMES_BNL / "run_fastframes.sh"), "parquet"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "unknown format: parquet" in result.stderr

    def test_ttree_keeps_its_working_directory_and_config(self):
        # The TTree job's input directory is maintained by hand on GPFS.
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert re.search(
            r'ttree\)\s+variant_suffix=""\s+'
            r"working_dir=/atlasgpfs01/usatlas/data/qlei\s+"
            r"config=mc20e_example_config\.yml\s+;;",
            text,
        )

    def test_rntuple_gets_its_own_directory_filled_from_the_repo(self):
        # Sharing the TTree job's directory would share its logs and output.
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert re.search(
            r'rntuple\)\s+variant_suffix="_rntuple"\s+'
            r"working_dir=/atlasgpfs01/usatlas/data/qlei/fastframes_rntuple\s+"
            r"config=mc20e_example_config_rntuple\.yml\b",
            text,
        )
        assert 'mkdir -p "${working_dir}/input" "${working_dir}/output"' in text
        for name in (
            "mc20e_example_config_rntuple.yml",
            "mc20e_filelist_rntuple.txt",
            "mc20e_sumweights.txt",
        ):
            assert name in text.split("rntuple)")[1].split(";;")[0]

    def test_run_script_records_setup_complete_without_a_runtime_dollar(self):
        # See the matching coffea test: ALRB expands \\$ in -r strings early.
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert "\\$(" not in text
        assert "date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log" in text

    def test_run_script_names_logs_and_log_directory_by_format(self):
        text = (FASTFRAMES_BNL / "run_fastframes.sh").read_text()
        assert 'log_file="fastframes${variant_suffix}.log"' in text
        assert (
            'output_dir="/atlasgpfs01/usatlas/data/qlei/logs/'
            'FastFrames_NTuple${variant_suffix}/${start_time}"'
        ) in text
        assert 'cd "${working_dir}" || exit' in text
        assert "-c ${working_dir}/input/${config}" in text
        assert "tee ${log_file}" in text

    def test_rntuple_sub_differs_from_the_ttree_sub_only_in_arguments_and_logs(self):
        ttree = (FASTFRAMES_BNL / "fastframes_el9.sub").read_text()
        rntuple = (FASTFRAMES_BNL / "fastframes_el9_rntuple.sub").read_text()
        expected = ttree.replace("myjob.", "myjob_rntuple.").replace(
            "Queue 1", "Arguments = rntuple\n\nQueue 1"
        )
        assert rntuple == expected

    def test_rntuple_cron_differs_from_the_ttree_cron_only_in_its_identity(self):
        ttree = (FASTFRAMES_BNL / "crontab_fastframes.sh").read_text()
        rntuple = (FASTFRAMES_BNL / "crontab_fastframes_rntuple.sh").read_text()
        expected = ttree
        for old, new in [
            (
                'log_base="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple"',
                'log_base="/atlasgpfs01/usatlas/data/qlei/logs/FastFrames_NTuple_rntuple"',
            ),
            ('log_output="fastframes.log"', 'log_output="fastframes_rntuple.log"'),
            (
                'job_dir="/usatlas/u/qlei/test/fastframes"',
                'job_dir="/usatlas/u/qlei/test/fastframes_rntuple"',
            ),
            ("/fastframes_el9.sub", "/fastframes_el9_rntuple.sub"),
            ('pixi_job="fastframes"', 'pixi_job="fastframes-rntuple"'),
        ]:
            assert old in expected
            expected = expected.replace(old, new)
        assert rntuple == expected

    def test_crontab_runs_the_rntuple_twin_on_the_same_schedule(self):
        # See the matching coffea test: the pair must run under the same load.
        assert cron_schedule("fastframes/BNL/crontab_fastframes.sh") == cron_schedule(
            "fastframes/BNL/crontab_fastframes_rntuple.sh"
        )
