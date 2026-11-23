"""Tests for the BNL benchmark job scripts (no ATLAS software or HTCondor required)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COFFEA_BNL = REPO_ROOT / "NTuple_Hist" / "coffea" / "BNL"
FASTFRAMES_BNL = REPO_ROOT / "NTuple_Hist" / "fastframes" / "BNL"
CONVERSION = REPO_ROOT / "NTuple_Hist" / "rntuple_conversion"


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
