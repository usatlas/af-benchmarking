"""Behaviour tests for the UC-ODF EventLoop Python files, with ROOT stubbed out."""

import importlib.util
import re
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EVENTLOOP_FILES = [
    "NTuple_Hist/event_loop/UC-ODF/columnar/event_loop_arrays.py",
    "NTuple_Hist/event_loop/UC-ODF/standard/event_loop_noarrays.py",
]


@pytest.fixture
def load_eventloop(monkeypatch):
    # ROOT only exists inside the ATLAS container, so a stand-in module is
    # enough: these tests exercise the error handling, not ROOT itself.
    fake_root = mock.MagicMock(name="ROOT")
    monkeypatch.setitem(sys.modules, "ROOT", fake_root)

    def load(relative_path):
        spec = importlib.util.spec_from_file_location(
            "eventloop_under_test", REPO_ROOT / relative_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, fake_root

    return load


@pytest.mark.parametrize("path", EVENTLOOP_FILES)
class TestPhotonEventloopErrors:
    # An unreadable ntuple must fail the job. Skipping it would report fewer
    # events with exit status 0, a plausible-looking but wrong benchmark.
    def test_file_that_cannot_be_opened_raises(self, load_eventloop, path):
        module, fake_root = load_eventloop(path)
        fake_root.TFile.Open.return_value = None
        with pytest.raises(
            RuntimeError, match=re.escape("Could not open file: a.root")
        ):
            module.photon_eventloop("a.root", None, {})

    def test_zombie_file_raises(self, load_eventloop, path):
        module, fake_root = load_eventloop(path)
        fake_root.TFile.Open.return_value.IsZombie.return_value = True
        with pytest.raises(
            RuntimeError, match=re.escape("Could not open file: a.root")
        ):
            module.photon_eventloop("a.root", None, {})

    def test_file_without_analysis_tree_raises_and_is_closed(
        self, load_eventloop, path
    ):
        module, fake_root = load_eventloop(path)
        fake_file = fake_root.TFile.Open.return_value
        fake_file.IsZombie.return_value = False
        fake_file.Get.return_value = None
        with pytest.raises(
            RuntimeError, match=re.escape("No tree named 'analysis' in a.root")
        ):
            module.photon_eventloop("a.root", None, {})
        fake_file.Close.assert_called_once()
