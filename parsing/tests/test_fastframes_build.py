"""Tests for fetching the FastFrames sources before the UC-ODF build."""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FASTFRAMES_DIR = REPO_ROOT / "NTuple_Hist" / "fastframes"
ODF_DIR = FASTFRAMES_DIR / "UC-ODF"
FETCH = "NTuple_Hist/fastframes/UC-ODF/fetch_fastframes_sources.sh"
BUILD = ODF_DIR / "build_fastframes.sh"
CUSTOM_CLASS_FILES = [
    "CMakeLists.txt",
    "Root/LinkDef.h",
    "Root/TutorialClass.cc",
    "TutorialClass/TutorialClass.h",
]
# Fixed identity so the test commits do not depend on the machine's git config
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.org",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.org",
}


def git(*args, cwd):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **GIT_ENV},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def upstream(tmp_path):
    """A local git repository standing in for the FastFrames remote."""
    path = tmp_path / "upstream"
    path.mkdir()
    git("init", "-q", cwd=path)
    commits = []
    for version in ("first", "second"):
        (path / "version.txt").write_text(version)
        git("add", "version.txt", cwd=path)
        git("commit", "-q", "-m", version, cwd=path)
        commits.append(git("rev-parse", "HEAD", cwd=path))
    return path, commits


def run_fetch(ff_dir, url, commit):
    return subprocess.run(
        ["bash", FETCH],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "FF_DIR": str(ff_dir),
            "FASTFRAMES_URL": str(url),
            "FASTFRAMES_COMMIT": commit,
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


class TestFetchFastframesSources:
    def test_script_is_executable_and_valid_bash(self):
        path = REPO_ROOT / FETCH
        assert path.is_file()
        assert os.access(path, os.X_OK)
        subprocess.run(["bash", "-n", str(path)], check=True)

    def test_requires_ff_dir(self):
        env = {k: v for k, v in os.environ.items() if k != "FF_DIR"}
        result = subprocess.run(
            ["bash", FETCH],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert "FF_DIR" in result.stdout + result.stderr

    def test_clones_fastframes_at_the_pinned_commit(self, tmp_path, upstream):
        url, (first, _) = upstream
        ff_dir = tmp_path / "ff"
        result = run_fetch(ff_dir, url, first)
        assert result.returncode == 0, result.stderr
        assert git("rev-parse", "HEAD", cwd=ff_dir / "FastFrames") == first

    def test_copies_the_custom_class_sources(self, tmp_path, upstream):
        url, (first, _) = upstream
        ff_dir = tmp_path / "ff"
        assert run_fetch(ff_dir, url, first).returncode == 0
        for name in CUSTOM_CLASS_FILES:
            assert (ff_dir / "TutorialClass" / name).read_text() == (
                ODF_DIR / "TutorialClass" / name
            ).read_text()

    def test_second_run_keeps_the_clone_and_restores_edited_sources(
        self, tmp_path, upstream
    ):
        url, (first, _) = upstream
        ff_dir = tmp_path / "ff"
        assert run_fetch(ff_dir, url, first).returncode == 0
        marker = ff_dir / "FastFrames" / "marker.txt"
        marker.write_text("kept")
        (ff_dir / "TutorialClass" / "CMakeLists.txt").write_text("edited")

        assert run_fetch(ff_dir, url, first).returncode == 0
        assert marker.read_text() == "kept"
        assert (ff_dir / "TutorialClass" / "CMakeLists.txt").read_text() == (
            ODF_DIR / "TutorialClass" / "CMakeLists.txt"
        ).read_text()

    def test_fails_when_an_existing_clone_is_at_another_commit(
        self, tmp_path, upstream
    ):
        # Rebuilding a different FastFrames than the one benchmarked elsewhere
        # would silently change what is measured
        url, (first, second) = upstream
        ff_dir = tmp_path / "ff"
        assert run_fetch(ff_dir, url, first).returncode == 0

        result = run_fetch(ff_dir, url, second)
        assert result.returncode != 0
        assert second in result.stdout + result.stderr


class TestCustomClassSources:
    @pytest.mark.parametrize("name", CUSTOM_CLASS_FILES)
    def test_source_file_is_in_the_repo(self, name):
        assert (ODF_DIR / "TutorialClass" / name).is_file()

    def test_class_source_matches_the_copy_kept_for_the_other_sites(self):
        # Two copies of the same code must not drift apart. Whitespace is
        # ignored because the repo's hooks strip trailing whitespace.
        def words(path):
            return path.read_text().split()

        assert words(ODF_DIR / "TutorialClass" / "Root" / "TutorialClass.cc") == words(
            FASTFRAMES_DIR / "TutorialClass.cc"
        )


class TestBuildScriptFetchesSources:
    def test_build_script_runs_the_fetch_step_first(self):
        text = BUILD.read_text()
        assert "fetch_fastframes_sources.sh" in text
        assert text.index("fetch_fastframes_sources.sh") < text.index("atlasLocalSetup")
