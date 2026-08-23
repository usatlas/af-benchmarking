# CI Validation Workflow

**File:** `.github/workflows/ci.yml`

This workflow validates that the parsing and upload machinery itself works
correctly, using fixture logs checked into the repository rather than live
cluster data — it does not run real benchmark jobs.

/// warning | A pull request also triggers real benchmark jobs

Opening or updating a pull request against `main` does not only trigger this
workflow — it also triggers [`uchicago.yml`](benchmarks.md), which runs all 11
real benchmark jobs on the actual UChicago self-hosted runner
(`arc-runner-set-uchicago`). That trigger is gated only by a fork/dependabot
check, not by which files changed, so a documentation-only PR still runs real
EVNT/TRUTH3/Rucio/etc jobs on live UC infrastructure unless it comes from a fork
or dependabot.

///

## Trigger

The workflow runs:

- **On every push**, to any branch
- **On pull requests** to `main`
- **Manually** via `workflow_dispatch`

Runs for the same workflow and ref cancel any still-in-progress run
(`concurrency.cancel-in-progress: true`), and the workflow only requests
`contents: read` at the top level.

## Jobs

Three independent jobs run in parallel — none depend on another:

| Job             | Runner                    | Validates                                                             |
| --------------- | ------------------------- | --------------------------------------------------------------------- |
| `test-actions`  | `arc-runner-set-uchicago` | The `setup-globus` composite action runs on a real self-hosted runner |
| `test-handlers` | `ubuntu-latest`           | The parser's Python unit tests (`parsing/tests/`)                     |
| `test-parser`   | `ubuntu-latest`           | The `parse` action, integration-tested against 7 real log formats     |

### `test-actions`

Checks out the repo and runs `./.github/actions/setup-globus` with the
`VOMS_USERCERT`/`VOMS_USERKEY` secrets. This is a smoke test — success means the
composite action completed without error on the actual self-hosted runner it
will run on in `uchicago.yml`.

The job is skipped for pull requests from forks
(`github.event.pull_request.head.repo.fork == false`), since forked PRs can't
access repository secrets and shouldn't be granted access to the self-hosted
runner.

### `test-handlers`

Sets up the `kibana` pixi environment and runs:

```bash
pixi run -e kibana test
```

which is the pixi task alias (`pixi.toml`) for `pytest parsing/tests/`. This
runs the parser's unit test suite directly against the Python package —
`parsing/base_parser.py` and `parsing/scripts/ci_parse.py` — without going
through the composite action. It checks that the `=== BENCHMARK ===` block
extractor returns the last block when a log contains retries, that
`submitTime`/`queueTime`/`runTime`/`status`/`setupTime`/`cpuPercent`/`maxRssKb`
are derived correctly, and that a fully-assembled payload passes schema
validation.

### `test-parser`

Runs the `parse` composite action itself — not just the underlying Python —
against a matrix of real log fixtures under `parsing/example-logs/`:

| `log-file`               | `log-type`   |
| ------------------------ | ------------ |
| `coffea_hist.log`        | `coffea`     |
| `eventloop_arrays.log`   | `eventloop`  |
| `eventloop_noarrays.log` | `eventloop`  |
| `log.generate`           | `evnt`       |
| `fastframes.log`         | `fastframes` |
| `rucio.log`              | `rucio`      |
| `log.Derivation`         | `truth3`     |

{% raw %}

```yaml
- name: parse ${{ matrix.log-type }} log
  uses: ./.github/actions/parse
  with:
    job: ${{ matrix.log-type }}
    log-file: parsing/example-logs/${{ matrix.log-file }}
    log-type: ${{ matrix.log-type }}
    cluster: UC-AF
    kibana-token: "our-token"
    kibana-kind: "our-index"
    host: "our-host"
    os: alma9
    mode: batch
    containerized: "false"
```

{% endraw %}

No `secrets.*` are used here — the token/kind/host values are dummy literals,
since this job never uploads anywhere.

**`log-type` is metadata only.** `parse_atlas_log` (in `parsing/base_parser.py`)
does not branch on it — the exact same `=== BENCHMARK ===` block extractor
handles every log type uniformly. The matrix exists to prove the action works
across every real-world log format the AFs actually produce (different tools
writing wildly different surrounding log content), not to exercise different
parsing code paths.

**This job validates parsing, not uploading.** There is no step here that calls
`./.github/actions/upload` — the `upload` action is only exercised by the real
benchmark jobs in `uchicago.yml`. A regression in the upload action's `curl`
invocation would not be caught by CI.

## Next Steps

- Learn about the [parsing and upload action](parsing.md)
- See the [UChicago benchmark workflow](benchmarks.md) for how these actions are
  used with real benchmark data
- Check the [development guide](development.md) for local testing
