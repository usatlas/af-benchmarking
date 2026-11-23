"""Tests for the BNL benchmark job scripts (no ATLAS software or HTCondor required)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COFFEA_BNL = REPO_ROOT / "NTuple_Hist" / "coffea" / "BNL"
FASTFRAMES_BNL = REPO_ROOT / "NTuple_Hist" / "fastframes" / "BNL"
CONVERSION = REPO_ROOT / "NTuple_Hist" / "rntuple_conversion"


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
