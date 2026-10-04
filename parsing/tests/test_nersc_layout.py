"""Static checks on the NERSC job files.

These pin the qlei migration: no file a NERSC job reads may still point at
the old selbor account, and every repo path a NERSC script or sub file
references must exist (several pointed at a pre-restructure layout).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# The interactive TRUTH3 variants (EL9_i, CentOS7_i) are deliberately out of
# scope and still reference selbor, so only the batch subdirectories are listed.
NERSC_DIRS = [
    "TRUTH3/NERSC/EL9",
    "TRUTH3/NERSC/CentOS7",
    "EVNT/NERSC",
    "NTuple_Hist/coffea/NERSC",
    "NTuple_Hist/event_loop/NERSC",
    "NTuple_Hist/fastframes/NERSC",
]
NERSC_EXTRA_FILES = [
    "Rucio/cron_rucio_nersc.sh",
    "Rucio/rucio_nersc_sub.sh",
]
TEXT_SUFFIXES = {".sh", ".py", ".yml", ".json", ".txt"}
# The photon eventloop job is a legacy predecessor of the columnar/standard
# jobs (UC CI and the docs only run those two) and is left untouched.
EXCLUDED_FILES = {
    "NTuple_Hist/event_loop/NERSC/run_photon_eventloop.sh",
    "NTuple_Hist/event_loop/NERSC/photon_ABCD_eventloop.py",
}

# Matches ~/AF-Benchmarking/<path>, $HOME/AF-Benchmarking/<path> and
# "$HOME"/AF-Benchmarking/<path>; group 1 is the repo-relative path.
REPO_REF = re.compile(r'(?:~|"?\$HOME"?)/AF-Benchmarking/([A-Za-z0-9_./-]+)')


def nersc_files():
    files = [
        path
        for directory in NERSC_DIRS
        for path in (REPO / directory).rglob("*")
        if path.is_file()
        and path.suffix in TEXT_SUFFIXES
        and str(path.relative_to(REPO)) not in EXCLUDED_FILES
    ]
    files += [REPO / name for name in NERSC_EXTRA_FILES]
    return sorted(files)


def nersc_shell_scripts():
    return [path for path in nersc_files() if path.suffix == ".sh"]


def rel(path):
    return str(path.relative_to(REPO))


def sub_files():
    return [path for path in nersc_shell_scripts() if path.name.endswith("_sub.sh")]


def srun_target(sub_file):
    """Repo-relative path of the script a sub file runs with srun.

    Searches from the srun line onward because the path can sit on a
    backslash-continued line (Rucio/rucio_nersc_sub.sh).
    """
    text = sub_file.read_text()
    srun = re.search(r"^srun ", text, re.M)
    assert srun, f"{rel(sub_file)}: no srun line"
    match = REPO_REF.search(text, srun.start())
    assert match, f"{rel(sub_file)}: srun has no AF-Benchmarking path"
    return match.group(1)


class TestNerscQleiPaths:
    @pytest.mark.parametrize("path", nersc_files(), ids=rel)
    def test_no_selbor_reference(self, path):
        assert "selbor" not in path.read_text()

    def test_rucio_nersc_branch_has_no_selbor(self):
        text = (REPO / "Rucio" / "rucio_script.sh").read_text()
        block = text.split("    nersc)", 1)[1].split(";;", 1)[0]
        assert "selbor" not in block

    def test_rucio_sub_has_no_foreign_mail_user(self):
        text = (REPO / "Rucio" / "rucio_nersc_sub.sh").read_text()
        assert "--mail-user" not in text


class TestNerscRepoReferences:
    @pytest.mark.parametrize("path", nersc_shell_scripts(), ids=rel)
    def test_referenced_repo_paths_exist(self, path):
        missing = [
            ref
            for ref in REPO_REF.findall(path.read_text())
            if not (REPO / ref.rstrip("/")).exists()
        ]
        assert missing == []

    @pytest.mark.parametrize("path", sub_files(), ids=rel)
    def test_srun_target_is_executable(self, path):
        target = REPO / srun_target(path)
        assert os.access(target, os.X_OK), f"{rel(target)} is not executable"

    @pytest.mark.parametrize("path", nersc_shell_scripts(), ids=rel)
    def test_bash_syntax(self, path):
        result = subprocess.run(
            ["bash", "-n", str(path)], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
