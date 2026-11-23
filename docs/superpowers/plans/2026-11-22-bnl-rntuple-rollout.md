# BNL RNTuple Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give BNL RNTuple "twin" benchmarks for coffea, EventLoop (columnar +
standard), and FastFrames, matching what UChicago/UC-ODF already report in
Kibana, and bump BNL's FastFrames/EventLoop environment to StatAnalysis 0.7.3
(the version FastFrames' RNTuple support requires).

**Architecture:** Each existing BNL job script gains a `format="${1:-ttree}"`
(or `--format` for the Python payload) argument that picks a different input
file and log name — the same script serves both formats, exactly like UC/UC-ODF.
Each new `-rntuple` variant gets its own HTCondor `.sub` file and its own cron
wrapper (BNL has no shared submit-and-upload script like SLAC/NERSC; every job
type already has its own near-identical ~94-line
condor_submit/condor_wait/parse/upload wrapper, and this plan follows that
existing convention rather than introducing a new one).

**Tech Stack:** bash, HTCondor (`condor_submit`/`condor_wait`), Python
(coffea/awkward/PyROOT), ALRB/CVMFS, StatAnalysis 0.7.3.

**Spec:** `docs/superpowers/specs/2026-11-22-rntuple-rollout-design.md`

## Global Constraints

- StatAnalysis 0.7.3 bundles Python 3.10.6 (confirmed live on NERSC and SLAC) —
  FastFrames and EventLoop get this Python; it is not the Python 3.13 task.
- `coffea` gets Python 3.13 via `lsetup python <build>` — exact build string
  must be confirmed live first (see Task 1).
- RNTuple job naming: `<job>-rntuple` in the Kibana `job` field (e.g.
  `coffea-rntuple`, `eventloop-columnar-rntuple`, `fastframes-rntuple`);
  `log-type` stays the base type. No schema change needed.
- Every RNTuple job is the same script as its TTree sibling, dispatched on a
  `format` argument — never a separate script file.
- FastFrames build trees cannot be copied between machines — CMake bakes
  absolute paths. BNL has no existing `build_fastframes.sh`; this plan writes
  one.
- BNL's existing coffea/EventLoop datasets live under
  `/atlasgpfs01/usatlas/data/jroblesgo/` — a different account than `qlei`,
  which runs these jobs. Pre-existing, not introduced by this plan. The RNTuple
  conversion output's ownership/writability under that directory must be
  confirmed live before Task 4 (see its Step 1).

## Review Focus

- A `format` argument wired to the wrong dataset/config, so the RNTuple job
  silently benchmarks the TTree file (or vice versa) and nobody notices because
  both "succeed." → Every format-dispatch task's test asserts the actual file
  path/config selected for each format value, not just that the script runs.
- The StatAnalysis 0.7.3 bump silently changing the already-validated TTree
  FastFrames/EventLoop jobs' output (new ROOT version, different numeric
  result). → Tasks 2 and 3 each include running the _existing_ TTree job under
  0.7.3 and confirming it still completes with a sane, non-empty histogram
  before anything RNTuple-specific is added.
- `qlei` lacking write permission under `jroblesgo`'s directory, silently
  failing the RNTuple conversion or writing it somewhere inconsistent with where
  the job scripts expect to find it. → Task 4 Step 1 checks this explicitly
  before submitting any conversion job.
- RNTuple reading crashing under ROOT 6.38 the way UC's own code warns it can
  under 6.34 (`RNTupleView` segfault on destroy) — an API that's still
  `Experimental`. → Task 3's validation step runs UC's exact RNTuple-reading
  code against an already-converted file under BNL's new StatAnalysis 0.7.3
  before Task 6 wires it into a scheduled job.
- A FastFrames build that compiles but is silently wrong (the
  empty-`CMAKE_INSTALL_PREFIX` class of bug hit during the NERSC migration). →
  Task 2's build step requires the job to actually run and produce a
  non-trivial, non-zero-entry histogram, not just "the build finished."

---

### Task 1: coffea — Python 3.13

**Files:**

- Modify: `NTuple_Hist/coffea/BNL/run_example.sh`

**Interfaces:**

- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on (fully independent of the rest of this
  plan).

- [ ] **Step 1: Confirm the exact Python 3.13 build string available via ALRB**

Run on a BNL login node inside the same `-c el9` container this job already
uses:

```bash
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c el9 -r "lsetup python -h"
```

Expected: a list of available `python <version>-x86_64-el9` build strings.
Record the exact 3.13.x string (UC/UC-ODF/NERSC currently use
`'python 3.9.22-x86_64-el9'` as the pattern to match).

- [ ] **Step 2: Add the `lsetup python` call to the `-r` string**

In `run_example.sh`'s `-r "..."` string (currently starts with
`date >> split.log &&\`), insert
`lsetup 'python <3.13.x string>-x86_64-el9' &&\` immediately after the opening
`date` line and before `python3 -m venv venv`, so the venv is built against 3.13
rather than the container's own Python.

- [ ] **Step 3: Run the job once by hand and verify**

```bash
condor_submit /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/coffea/BNL/coffea_el9.sub
```

Expected: job completes; inspect its log for the venv's Python version (e.g.
have the `-r` string also run `./venv/bin/python --version >> split.log`
temporarily, or check interactively) and confirm `3.13.x`; confirm
`coffea.root`/`coffea_hist.log` are still produced as before (no regression).

- [ ] **Step 4: Commit**

```bash
git add NTuple_Hist/coffea/BNL/run_example.sh
git commit -m "feat(bnl): run coffea under Python 3.13"
```

---

### Task 2: FastFrames — StatAnalysis 0.7.3 + build FastFrames 7.2.0

**Files:**

- Create: `NTuple_Hist/fastframes/BNL/build_fastframes.sh` (adapt from
  `NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh`, which is already
  site-generic — parameterized by `FF_DIR`/`JOBS` env vars; change nothing but
  the default `FF_DIR` if the existing script hardcodes one UC-ODF path)
- Modify: `NTuple_Hist/fastframes/BNL/run_fastframes.sh`

**Interfaces:**

- Consumes: nothing from other tasks.
- Produces: `FF_DIR` (the built FastFrames 7.2.0 + `TutorialClass` tree at BNL)
  — Task 7 (FastFrames RNTuple twin) uses this same build; no other task depends
  on it.

- [ ] **Step 1: Write `build_fastframes.sh`**

Copy `NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh` to
`NTuple_Hist/fastframes/BNL/build_fastframes.sh` unchanged except any
UC-ODF-specific default path; it already does `asetup StatAnalysis,0.7.3` +
builds `FastFrames` then `TutorialClass` against it with an explicit
`-DCMAKE_INSTALL_PREFIX` (the fix for the empty-prefix bug from the NERSC
migration).

- [ ] **Step 2: Run the build on a BNL compute node**

```bash
FF_DIR=/atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3 \
  bash NTuple_Hist/fastframes/BNL/build_fastframes.sh
```

Expected: build completes with no "Cannot get class TutorialClass"-style error;
`${FF_DIR}/TutorialClass/build/setup.sh` exists.

- [ ] **Step 3: Point `run_fastframes.sh` at the new build and bump the
      version**

In `NTuple_Hist/fastframes/BNL/run_fastframes.sh`: change
`asetup StatAnalysis,0.6.3` to `asetup StatAnalysis,0.7.3`; change
`source /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial/TutorialClass/build/setup.sh`
to
`source /atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3/TutorialClass/build/setup.sh`.

- [ ] **Step 4: Run the existing TTree FastFrames job and confirm no
      regression**

```bash
condor_submit /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/fastframes/BNL/fastframes_el9.sub
```

Expected: job completes; `example_FS.root` (or whatever
`mc20e_example_config.yml` names its output) is produced with a non-zero-entry
histogram, same as before the version bump.

- [ ] **Step 5: Commit**

```bash
git add NTuple_Hist/fastframes/BNL/build_fastframes.sh NTuple_Hist/fastframes/BNL/run_fastframes.sh
git commit -m "feat(bnl): build FastFrames 7.2.0 under StatAnalysis 0.7.3"
```

---

### Task 3: EventLoop — StatAnalysis 0.7.3 + validate RNTuple reading

**Files:**

- Modify: `NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh`
- Modify: `NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh`

**Interfaces:**

- Consumes: nothing from other tasks.
- Produces: confirmation (not code) that `r.Experimental.RNTupleReader.Open`
  works under StatAnalysis 0.7.3 — Task 6 depends on this validation having
  passed before it's built.

- [ ] **Step 1: Bump both EventLoop scripts' StatAnalysis version**

Change `asetup StatAnalysis,0.6.3` to `asetup StatAnalysis,0.7.3` at line 13 of
both `run_eventloop_arrays.sh` and `run_eventloop_noarrays.sh`.

- [ ] **Step 2: Run both existing TTree jobs and confirm no regression**

```bash
condor_submit /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/columnar/eventloop_arrays.sub
condor_submit /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/standard/eventloop_noarrays.sub
```

Expected: both complete, both still produce a non-zero-entry output histogram
(ignore the pre-existing, out-of-scope `event_loop_noarrays_output_hist.root`
filename that `eventloop_arrays.py` also writes under — not introduced by this
plan, not fixed by it either).

- [ ] **Step 3: Validate RNTuple reading under 0.7.3 (gates Task 6)**

Write a throwaway script (not committed) that mirrors
`NTuple_Hist/event_loop/UC/columnar/event_loop_arrays.py`'s
`photon_eventloop_rntuple` function exactly, pointed at one of UC's
already-converted RNTuple files (if BNL can read UC's AFS/shared path) or any
other already-converted `_RNTuple.root` file reachable from BNL. Run it under
`asetup StatAnalysis,0.7.3` and confirm `RNTupleReader.Open(...)` opens the file
and the event loop completes without a segfault.

If it segfaults: stop here and report back before Task 6 — this plan's Task 6
assumes this step passed.

- [ ] **Step 4: Commit**

```bash
git add NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh
git commit -m "feat(bnl): run EventLoop under StatAnalysis 0.7.3"
```

---

### Task 4: Convert BNL's ntuple dataset to RNTuple

**Files:**

- Create: `NTuple_Hist/rntuple_conversion/BNL/convert.sub`
- Create: `NTuple_Hist/rntuple_conversion/BNL/inputs.txt`
- Consumes (unchanged, reused as-is):
  `NTuple_Hist/rntuple_conversion/UC/convert_ttree_to_rntuple.py`,
  `NTuple_Hist/rntuple_conversion/UC/convert_job.sh` — both are already generic
  (absolute input path in, sibling `_RNTuple.root` output; no UC-hardcoded
  paths).

**Interfaces:**

- Consumes: nothing from other tasks.
- Produces:
  `<dataset-dir>/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS_RNTuple.root/`
  (sibling of the existing TTree dataset directory) — Tasks 5 and 6 read this
  path.

- [ ] **Step 1: Confirm `qlei` can write under `jroblesgo`'s dataset directory**

```bash
touch /atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/.qlei-write-test \
  && echo "writable" && rm /atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/.qlei-write-test
```

If this fails: the RNTuple copy cannot be a sibling of the original under
`jroblesgo`'s tree. In that case, write the converted files to a `qlei`-owned
directory instead (e.g.
`/atlasgpfs01/usatlas/data/qlei/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS_RNTuple.root/`)
and use that path in Tasks 5/6's dataset JSON and `DATASET_PATHS` instead of a
true sibling path. Record which case applies — it changes the exact path used in
Tasks 5 and 6.

- [ ] **Step 2: Write `inputs.txt`**

```bash
find /atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root -name '*.root' -type f | sort \
  > NTuple_Hist/rntuple_conversion/BNL/inputs.txt
```

- [ ] **Step 3: Write `convert.sub`**

Adapt `NTuple_Hist/rntuple_conversion/UC/convert.sub`'s Condor syntax
(`queue input from inputs.txt`) to BNL's house style (see
`NTuple_Hist/coffea/BNL/coffea_el9.sub` for the `Output`/`Error`/`Log` path
convention this repo already uses at BNL); `Executable` points at
`NTuple_Hist/rntuple_conversion/UC/convert_job.sh` directly (it's site-generic,
no need to copy it) with `Arguments = $(input)`.

- [ ] **Step 4: Submit and verify**

```bash
condor_submit NTuple_Hist/rntuple_conversion/BNL/convert.sub
condor_wait <log path from the .sub file>
```

Expected: each job prints an `OK ...` summary line (per
`convert_job.sh`/`convert_ttree_to_rntuple.py`'s own validation: entry counts
match, no mismatched sums); `_RNTuple.root` sibling files now exist.

- [ ] **Step 5: Commit**

```bash
git add NTuple_Hist/rntuple_conversion/BNL/convert.sub NTuple_Hist/rntuple_conversion/BNL/inputs.txt
git commit -m "feat(bnl): add the RNTuple conversion Condor job"
```

---

### Task 5: coffea RNTuple twin

**Files:**

- Modify: `NTuple_Hist/coffea/BNL/run_example.sh`
- Replace: `NTuple_Hist/coffea/BNL/example.py` with
  `NTuple_Hist/coffea/UC/example.py`'s content, unchanged — confirmed that file
  has no UC-hardcoded paths; `DATASET_DIR` resolves relative to
  `Path(__file__)`, and BNL already has its own sibling
  `single_campaign_mc20e_dataset_runnable/` directory.
- Create:
  `NTuple_Hist/coffea/BNL/single_campaign_mc20e_dataset_runnable/af_v2_700402_rntuple.json`
  (copy of the existing `af_v2_700402.json`, each file path updated to the
  `_RNTuple.root` sibling from Task 4)
- Create: `NTuple_Hist/coffea/BNL/coffea_el9_rntuple.sub`
- Create: `NTuple_Hist/coffea/BNL/cron_example_rntuple.sh`
- Modify: `CrontabFiles/crontab_bnl.txt`

**Interfaces:**

- Consumes: Task 4's `_RNTuple.root` path.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace `example.py`**

Copy `NTuple_Hist/coffea/UC/example.py` over `NTuple_Hist/coffea/BNL/example.py`
verbatim (it already has the `--format` argparse, `DATASET_JSONS` dict,
`VirtualProcessor`/`runner_fileset`/ `run_dask`/`run_virtual` split — coffea's
dask-awkward mode crashes on RNTuple input, so the RNTuple path runs through
`processor.Runner` instead; this is already-working code to reuse, not to
redesign).

- [ ] **Step 2: Write the RNTuple dataset JSON**

Copy `af_v2_700402.json` to `af_v2_700402_rntuple.json` in the same directory;
update every file's path from
`.../user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/...` to the
`_RNTuple.root` equivalent (same per-file entry counts/metadata — the conversion
preserves them).

- [ ] **Step 3: Add format dispatch to `run_example.sh`**

Mirror `NTuple_Hist/coffea/UC/run_example.sh`'s `format="${1:-ttree}"` + `case`
block (picks `coffea_hist.log` vs `coffea_hist_rntuple.log`), and pass
`--format "${format}"` to the `python3`/venv invocation in the `-r` string.

- [ ] **Step 4: Write `coffea_el9_rntuple.sub`**

Copy `coffea_el9.sub`, changing only `Executable`'s arguments: add
`Arguments = rntuple` and point `Output`/`Error`/`Log` at a distinct
`myjob_rntuple.$(Cluster).$(Process).{out,err,log}` path so it doesn't collide
with the TTree job's condor log files.

- [ ] **Step 5: Write `cron_example_rntuple.sh`**

Copy `cron_example.sh`, changing: `log_output="coffea_hist_rntuple.log"`,
`sub_file` to point at `coffea_el9_rntuple.sub`, `pixi_job="coffea-rntuple"`,
and `job_dir`/`log_base` to distinct paths (e.g. append `_rntuple`) so the two
variants' condor jobs and output-directory lookups never collide.

- [ ] **Step 6: Add the crontab entry**

In `CrontabFiles/crontab_bnl.txt`, add under the existing "Coffea Metrics"
section:
`0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/coffea/BNL/cron_example_rntuple.sh`

- [ ] **Step 7: Run by hand and verify**

```bash
bash /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/coffea/BNL/cron_example_rntuple.sh
```

Expected: completes, uploads with `job: coffea-rntuple`, `status: 0`, a sane
`runTime`.

- [ ] **Step 8: Commit**

```bash
git add NTuple_Hist/coffea/BNL/ CrontabFiles/crontab_bnl.txt
git commit -m "feat(bnl): add the coffea RNTuple benchmark"
```

---

### Task 6: EventLoop RNTuple twins (columnar + standard)

**Files:**

- Modify: `NTuple_Hist/event_loop/BNL/columnar/eventloop_arrays.py`
- Modify: `NTuple_Hist/event_loop/BNL/standard/eventloop_noarrays.py`
- Modify: `NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh`
- Modify: `NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh`
- Create: `NTuple_Hist/event_loop/BNL/columnar/eventloop_arrays_rntuple.sub`
- Create: `NTuple_Hist/event_loop/BNL/standard/eventloop_noarrays_rntuple.sub`
- Create: `NTuple_Hist/event_loop/BNL/columnar/cron_eventloop_arrays_rntuple.sh`
- Create:
  `NTuple_Hist/event_loop/BNL/standard/cron_eventloop_noarrays_rntuple.sh`
- Modify: `CrontabFiles/crontab_bnl.txt`

**Interfaces:**

- Consumes: Task 3's validation (must have passed) and Task 4's `_RNTuple.root`
  path.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Add the RNTuple reader function to both `.py` payloads**

Into `eventloop_arrays.py` and `eventloop_noarrays.py`, add
`photon_eventloop_rntuple` copied verbatim from
`NTuple_Hist/event_loop/UC/columnar/event_loop_arrays.py` (the
`RNTupleReader.Open`/`GetModel().GetDefaultEntry()`/`GetPtr[...]` pattern,
including its comment about the `Experimental` namespace and the destroy-a-view
segfault). Add
`EVENTLOOPS = {"ttree": photon_eventloop, "rntuple": photon_eventloop_rntuple}`
and an `argparse` `--format` option in `main()`, same shape as UC's.

- [ ] **Step 2: Update `DATASET_PATHS`/dataset dict**

Change the single hardcoded dataset path to a dict:

```python
DATASET_PATHS = {
    "ttree": "/atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/",
    "rntuple": "<path from Task 4 Step 1>",
}
```

Use whichever path Task 4 Step 1 determined (the true sibling under `jroblesgo`,
or the `qlei`-owned fallback).

- [ ] **Step 3: Add format dispatch to both `run_eventloop_*.sh`**

Mirror UC's `run_eventloop_arrays.sh`: `format="${1:-ttree}"`, `case` picking
the log filename, pass `--format "${format}"` to the Python payload.

- [ ] **Step 4: Write the two new `.sub` files and two new cron wrappers**

Same pattern as Task 5 Steps 4–5: copy the existing `.sub`/`cron_*.sh` pair for
each variant, pointing at `..._rntuple.sub`, with distinct condor log paths,
`pixi_job="eventloop-columnar-rntuple"` /
`pixi_job="eventloop-standard-rntuple"`, and distinct `job_dir`/`log_base`.

- [ ] **Step 5: Add the two crontab entries**

In `CrontabFiles/crontab_bnl.txt`, under "EventLoop Arrays Script" and
"EventLoop No Arrays Script" respectively.

- [ ] **Step 6: Run both by hand and verify**

```bash
bash /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/columnar/cron_eventloop_arrays_rntuple.sh
bash /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/standard/cron_eventloop_noarrays_rntuple.sh
```

Expected: both complete, upload with `job: eventloop-columnar-rntuple` /
`eventloop-standard-rntuple`, `status: 0`. Spot-check the output histogram has a
plausible nonzero entry count (not an empty/zero-event run silently
"succeeding") — see the design doc's anti-goal about this exact failure mode.

- [ ] **Step 7: Commit**

```bash
git add NTuple_Hist/event_loop/BNL/ CrontabFiles/crontab_bnl.txt
git commit -m "feat(bnl): add the EventLoop RNTuple benchmarks"
```

---

### Task 7: FastFrames RNTuple twin

**Files:**

- Create: `NTuple_Hist/fastframes/BNL/mc20e_filelist_rntuple.txt`
- Create: `NTuple_Hist/fastframes/BNL/mc20e_example_config_rntuple.yml`
- Modify: `NTuple_Hist/fastframes/BNL/run_fastframes.sh`
- Create: `NTuple_Hist/fastframes/BNL/fastframes_el9_rntuple.sub`
- Create: `NTuple_Hist/fastframes/BNL/crontab_fastframes_rntuple.sh`
- Modify: `CrontabFiles/crontab_bnl.txt`

**Interfaces:**

- Consumes: Task 2's `FF_DIR` build and Task 4's `_RNTuple.root` path.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write the RNTuple filelist**

Copy `mc20e_filelist.txt` to `mc20e_filelist_rntuple.txt`, updating each entry
to point at the `_RNTuple.root` sibling path from Task 4 (same file-name pattern
as the TTree list, same count of entries).

- [ ] **Step 2: Write the RNTuple config**

Copy `mc20e_example_config.yml` to `mc20e_example_config_rntuple.yml`, changing
only `input_filelist_path` to point at
`./NTuple_Hist/fastframes/BNL/mc20e_filelist_rntuple.txt` — confirmed via
`NTuple_Hist/fastframes/UC/mc20e_example_config.yml` vs
`mc20e_example_config_rntuple.yml` that this one line is the entire diff between
the two formats' configs.

- [ ] **Step 3: Add format dispatch to `run_fastframes.sh`**

Mirror `NTuple_Hist/fastframes/UC/run_fastframes.sh`'s `format="${1:-ttree}"`

- `case` picking `config`/`log_file`.

* [ ] **Step 4: Write the new `.sub` and cron wrapper**

Same pattern as Tasks 5/6: `fastframes_el9_rntuple.sub` with
`Arguments = rntuple` and distinct condor log paths;
`crontab_fastframes_rntuple.sh` with `log_output=fastframes_rntuple.log`,
`pixi_job="fastframes-rntuple"`, distinct `job_dir`/`log_base`.

- [ ] **Step 5: Add the crontab entry**

In `CrontabFiles/crontab_bnl.txt`, under "FastFrames Script".

- [ ] **Step 6: Run by hand and verify**

```bash
bash /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/fastframes/BNL/crontab_fastframes_rntuple.sh
```

Expected: completes, uploads with `job: fastframes-rntuple`, `status: 0`; the
output histogram has nonzero entries.

- [ ] **Step 7: Commit**

```bash
git add NTuple_Hist/fastframes/BNL/ CrontabFiles/crontab_bnl.txt
git commit -m "feat(bnl): add the FastFrames RNTuple benchmark"
```

---

### Task 8: Docs

**Files:**

- Modify: `docs/bnl/benchmarks.md`

**Interfaces:**

- Consumes: the final state of Tasks 1–7 (job names, paths, build steps).
- Produces: nothing (terminal task).

- [ ] **Step 1: Add the 4 new jobs to the Benchmark Jobs table**

Add rows for `coffea-rntuple`, `eventloop-columnar-rntuple`,
`eventloop-standard-rntuple`, `fastframes-rntuple`, matching
`docs/uchicago/benchmarks.md`'s "RNTuple twin" framing (one short paragraph
after the jobs table explaining the twin pattern, linking
`docs/workflows/rntuple-conversion.md`).

- [ ] **Step 2: Add a one-time-setup section**

BNL's page currently has no one-time-setup table (unlike NERSC's). Add one
covering: the FastFrames 7.2.0 build (`build_fastframes.sh`, `FF_DIR`), the
RNTuple conversion step (Task 4), and the Python 3.13 coffea `lsetup` build
string from Task 1.

- [ ] **Step 3: Build and link-check**

```bash
pixi run -e docs build
pixi run -e docs build-check
```

Expected: both pass (`--strict`, 0 link errors).

- [ ] **Step 4: Commit**

```bash
git add docs/bnl/benchmarks.md
git commit -m "docs(bnl): document the RNTuple benchmarks and StatAnalysis bump"
```

## Self-Review

**Spec coverage:** Goals 1–3 (RNTuple twins, StatAnalysis 0.7.3, FastFrames
build) → Tasks 2, 3, 5, 6, 7. Goal 4 (RNTuple conversion run locally) → Task 4.
Goal 5 (coffea Python 3.13) → Task 1. Goal 6 (parallel across sites) is a
cross-plan decision, not a BNL-specific task. Goal 7 (docs) → Task 8. All
design-doc goals covered.

**Step scan:** every code step names an exact file and either an exact value to
insert (version strings, job names, log filenames) or an exact existing
file/function to copy from; no step says "handle appropriately" or leaves a
value undetermined other than the two explicitly-flagged live-validation
unknowns (the Python 3.13 build string, and which path Task 4 resolves to), both
of which are resolved by an earlier step before anything depends on them.

**Type/name consistency:** `pixi_job` values (`coffea-rntuple`,
`eventloop-columnar-rntuple`, `eventloop-standard-rntuple`,
`fastframes-rntuple`) match the design doc's naming convention exactly and are
used consistently across Tasks 5–7's `.sub`/cron-wrapper/crontab steps.

**Review Focus:** all five items above have an owning task and an explicit check
in that task's steps, not just a step that runs the job and assumes success.

**Proportion:** this plan is longer than the design doc because BNL has no
shared wrapper to lean on (8 new files per the non-coffea job types vs.
SLAC/NERSC's single shared script), so each job type needs its own `.sub` + cron
wrapper spelled out; the bodies themselves are "copy file X, change value Y"
rather than full file transcripts.
