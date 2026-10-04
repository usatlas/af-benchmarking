"""Integration tests for parsing/utils/parse_upload.sh.

pixi and curl are replaced by stub executables on PATH, so the script's own
control flow (arguments, payload checks, HTTP status handling) runs for real
without parsing a real log or contacting LogStash.
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "parsing" / "utils" / "parse_upload.sh"

PIXI_STUB = r"""#!/bin/bash
printf '%s\n' "$@" > "$FAKE_LOG/pixi_args"
out=""
for arg in "$@"; do
  case "$arg" in --output=*) out="${arg#--output=}" ;; esac
done
if [ "${FAKE_PIXI_EMPTY:-0}" != 1 ]; then
  echo '{"job": "truth3"}' > "$out"
fi
"""

CURL_STUB = r"""#!/bin/bash
printf '%s\n' "$@" > "$FAKE_LOG/curl_args"
out=""
while [ $# -gt 0 ]; do
  if [ "$1" = "-o" ]; then out="$2"; shift; fi
  shift
done
echo ok > "$out"
printf '%s' "${FAKE_HTTP_CODE:-200}"
"""


def write_executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


@pytest.fixture
def sandbox(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "pixi", PIXI_STUB)
    write_executable(bin_dir / "curl", CURL_STUB)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".secrets").write_text(
        "export KIBANA_TOKEN=test-token\n"
        "export KIBANA_URI=https://logstash.example.org/\n"
    )
    output_dir = (
        tmp_path / "benchmarks" / "2026-10-04T00:00:00Z" / "TRUTH3_el9_container"
    )
    output_dir.mkdir(parents=True)
    (output_dir / "log.Derivation").write_text("log\n")
    (output_dir / "hostname.txt").write_text("nid001234\n")
    fake_log = tmp_path / "fake_log"
    fake_log.mkdir()
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(home),
        "FAKE_LOG": str(fake_log),
    }
    return {"env": env, "output_dir": output_dir, "fake_log": fake_log, "home": home}


def default_args(output_dir):
    return [
        "--cluster",
        "NERSC-AF",
        "--job",
        "truth3",
        "--log-type",
        "truth3",
        "--log-file",
        str(output_dir / "log.Derivation"),
        "--os",
        "alma9",
        "--mode",
        "batch",
        "--containerized",
        "true",
        "--output-dir",
        str(output_dir),
    ]


def run_script(sandbox, args=None, extra_env=None):
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            *(args if args is not None else default_args(sandbox["output_dir"])),
        ],
        env={**sandbox["env"], **(extra_env or {})},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def recorded(sandbox, name):
    return (sandbox["fake_log"] / name).read_text().splitlines()


class TestParseUploadSuccess:
    def test_forwards_metadata_to_ci_parse(self, sandbox):
        result = run_script(sandbox)
        assert result.returncode == 0, result.stdout + result.stderr
        args = recorded(sandbox, "pixi_args")
        out = sandbox["output_dir"]
        assert args[args.index("--cluster") + 1] == "NERSC-AF"
        assert args[args.index("--log-file") + 1] == str(out / "log.Derivation")
        assert "--token=test-token" in args
        assert "--kind=benchmark" in args
        assert "--host=nid001234" in args
        assert "--os=alma9" in args
        assert "--mode=batch" in args
        assert "--containerized=true" in args
        assert f"--output={out / 'payload.json'}" in args

    def test_posts_payload_to_kibana_uri(self, sandbox):
        result = run_script(sandbox)
        assert result.returncode == 0
        args = recorded(sandbox, "curl_args")
        assert "https://logstash.example.org/" in args
        assert f"@{sandbox['output_dir'] / 'payload.json'}" in args
        assert "Upload successful!" in result.stdout

    def test_host_falls_back_to_hostname(self, sandbox):
        (sandbox["output_dir"] / "hostname.txt").unlink()
        result = run_script(sandbox)
        assert result.returncode == 0
        expected = subprocess.run(
            ["hostname"], capture_output=True, text=True, check=True
        ).stdout.strip()
        assert f"--host={expected}" in recorded(sandbox, "pixi_args")


class TestParseUploadFailures:
    def test_empty_payload_is_not_uploaded(self, sandbox):
        result = run_script(sandbox, extra_env={"FAKE_PIXI_EMPTY": "1"})
        assert result.returncode == 1
        assert not (sandbox["fake_log"] / "curl_args").exists()

    def test_non_2xx_response_fails(self, sandbox):
        result = run_script(sandbox, extra_env={"FAKE_HTTP_CODE": "500"})
        assert result.returncode == 1
        assert "Upload failed" in result.stdout

    def test_missing_secrets_fails_before_parsing(self, sandbox):
        (sandbox["home"] / ".secrets").unlink()
        result = run_script(sandbox)
        assert result.returncode == 1
        assert "KIBANA_TOKEN" in result.stderr
        assert not (sandbox["fake_log"] / "pixi_args").exists()

    def test_missing_argument_exits_2(self, sandbox):
        args = default_args(sandbox["output_dir"])[:-2]
        result = run_script(sandbox, args=args)
        assert result.returncode == 2
        assert "--output-dir" in result.stderr

    def test_flag_without_value_exits_2(self, sandbox):
        args = [*default_args(sandbox["output_dir"])[:-1]]
        result = run_script(sandbox, args=args)
        assert result.returncode == 2

    def test_unknown_flag_exits_2(self, sandbox):
        result = run_script(
            sandbox, args=[*default_args(sandbox["output_dir"]), "--bogus", "x"]
        )
        assert result.returncode == 2
