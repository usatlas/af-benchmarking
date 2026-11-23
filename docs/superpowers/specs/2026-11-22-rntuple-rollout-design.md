# RNTuple benchmark rollout to BNL, SLAC, NERSC

## Intent and why

UChicago and UC-ODF already run RNTuple "twins" of the coffea, EventLoop, and
FastFrames benchmarks alongside their existing TTree versions (PRs #96/#97), so
Kibana has side-by-side TTree-vs-RNTuple numbers for those two sites. BNL, SLAC,
and NERSC don't have this yet. This project brings the same RNTuple benchmark
coverage to all three, in parallel, so every site this repo benchmarks reports
both formats.

Getting there requires one prerequisite: FastFrames' RNTuple support needs
FastFrames v7.0+, and building that version requires StatAnalysis 0.7.3 as the
build/run environment. BNL, SLAC, and NERSC currently run FastFrames under
StatAnalysis 0.6.2/0.6.3, so all three need that bump first. EventLoop is being
bumped to 0.7.3 alongside FastFrames too — not because it needs to unlock
anything, but because the alternative (leaving EventLoop on 0.6.x) is an
untested combination with its own open question (see "RNTuple reading under ROOT
6.36" below), and Qi chose to collapse that to a single, more standard
environment per site rather than carry two.

A separate, unrelated-but-adjacent piece of standardization is also in scope:
coffea (which never uses StatAnalysis/asetup at any site — it's a bare ALRB
container with pip-installed packages) should run under Python 3.13 at every
site, replacing the inconsistent state today (UC/UC-ODF/NERSC explicitly
`lsetup python 3.9.22`; BNL/SLAC don't pin a Python at all and ride the
container's system default).

## Dependencies / sequencing

**Resolved, 2026-11-22: no longer a blocker.** PR #91 (`docs/slac-benchmarks`)
squash-merged to `main` with all of PR #93's (`feat/nersc-qlei-migration`)
commits as ancestors, so `main` now has the shared, site-neutral
`parsing/utils/submit_and_upload.sh`, SLAC's refactor to use it, the full NERSC
job tree and `crontab_nersc.txt`, and `docs/workflows/rntuple-conversion.md` at
its new path — verified directly against `origin/main`. PR #93 itself is now
redundant (conflicting against the new `main`, since everything it would add is
already there) and should be closed rather than merged separately.

Everything below, which was written describing the end state "once #93/#91
land," now simply describes the current state of `main`. This project can be
built directly against `main` with no sequencing dependency left.

## Goals

- coffea, EventLoop (columnar + standard), and FastFrames each get a `-rntuple`
  twin at BNL, SLAC, and NERSC, matching UC/UC-ODF's job-naming convention
  (`<job>-rntuple` in the Kibana `job` field, `log-type` unchanged) and script
  pattern (one script, `--format ttree|rntuple` / positional arg, picks a
  different input file and log name).
- FastFrames and EventLoop at BNL, SLAC, and NERSC run under
  `asetup StatAnalysis,0.7.3` (currently 0.6.2 at SLAC/NERSC, 0.6.3 at BNL).
- A working FastFrames 7.2.0 + `TutorialClass` build exists at each of BNL,
  SLAC, and NERSC, built in place at that site (not copied — CMake bakes
  absolute paths, confirmed by the NERSC and UC-ODF builds already hitting
  this).
- An RNTuple copy of each site's own TTree ntuple dataset exists at that site,
  produced by running the conversion scripts locally against files already
  downloaded there — not transferred from UC or any other site.
- coffea runs under Python 3.13 (via `lsetup python <3.13 build>`) at all 5
  sites — added fresh at BNL/SLAC, bumped from 3.9.22 at UC/UC-ODF/NERSC.
- All three sites (BNL, SLAC, NERSC) are done in parallel, not sequentially.
- Each site's `docs/<site>/benchmarks.md` page documents the new jobs, the
  version bump, and the one-time conversion/build steps, mirroring how
  BNL/SLAC/NERSC's existing pages are structured.

## Non-goals

- UC and UC-ODF are untouched — they already have this.
- No change to EVNT, TRUTH3, or Rucio at any site.
- No change to the Kibana schema (`job` is an unconstrained `^[a-z0-9_-]+$`
  pattern; `<job>-rntuple` needs no schema update, confirmed by how UC/UC-ODF's
  rollout needed none).
- Not fixing the 10 findings from the #93/#91 code review in this project —
  those are tracked separately and are orthogonal to this work (though the
  benchmark_utils.sh duplication finding touches files this project also edits;
  see "What's left to the builder").
- Not solving `parsing/base_parser.py:80`'s exit_status gap or the Rucio
  pipefail/exit-status gap here — both predate this project and are already
  tracked as open follow-ups elsewhere.

## Anti-goals (would make this a failure even if it technically runs)

- Silently reporting RNTuple results that are actually reading the TTree file
  (or vice versa) because a path/format argument was wired wrong — this would
  look like success in Kibana while comparing nothing.
- Breaking any of BNL/SLAC/NERSC's existing, already-validated TTree
  EventLoop/FastFrames jobs as a side effect of the version bump (e.g. a ROOT
  6.36→6.38 behavior change nobody checked for).
- A FastFrames/TutorialClass build that "mostly builds" but silently produces
  wrong results, the way the empty-CMAKE_INSTALL_PREFIX bug did during the NERSC
  migration (caught then only because the job errored loudly with "Cannot get
  class TutorialClass" — a quieter failure mode could slip through).

## Constraints (established facts, not choices)

- **StatAnalysis 0.7.3 bundles Python 3.10.6**, confirmed by directly running
  `asetup StatAnalysis,0.7.3 && python3 --version` on both NERSC and SLAC. This
  is why Python 3.13 standardization is scoped to coffea only —
  FastFrames/EventLoop get whatever Python the StatAnalysis release bundles, and
  no currently-available StatAnalysis branch bundles 3.13.
- **RNTuple's reading API is still evolving.** UC's own working EventLoop
  RNTuple code opens files via `r.Experimental.RNTupleReader.Open(...)` — still
  in the `Experimental` namespace — with the comment "RNTupleView: destroying a
  view from PyROOT segfaults in this release," a workaround already needed under
  ROOT 6.34.04. This is not proven to behave identically under 0.7.3's ROOT
  6.38; see validation step 1 below.
- **FastFrames build trees cannot be copied between machines or sites** — CMake
  bakes absolute paths into `setup.sh`. Each site rebuilds from source, in
  place. (Already hit and solved once at NERSC and UC-ODF;
  `NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh` is already site-generic,
  parameterized by `FF_DIR`/`JOBS`, and reusable as the starting point for
  BNL/SLAC/NERSC's own build step.)
- **The RNTuple conversion scripts themselves are generic.**
  `NTuple_Hist/rntuple_conversion/UC/convert_ttree_to_rntuple.py` and
  `convert_job.sh` take an absolute input path and derive the sibling
  `_RNTuple.root` output; no UC-hardcoded paths in the conversion logic. Only
  `convert.sub` (Condor-specific) needs a real per-site rewrite: BNL can reuse
  the HTCondor `.sub` pattern directly, SLAC/NERSC need an `sbatch`-based
  equivalent (array job or submit-loop).
- **The RNTuple job-naming convention is `<job>-rntuple`** in the Kibana `job`
  field (e.g. `coffea-rntuple`, `eventloop-columnar-rntuple`,
  `fastframes-rntuple`), `log-type` staying the base type. Confirmed from
  UC/UC-ODF's GitHub Actions workflows and schema (no enum, so no schema change
  needed).
- **Each RNTuple job is "the same script, different argument"** — not a separate
  script file. UC's pattern: a `format="${1:-ttree}"` positional arg (or
  `--format` flag for the Python payload) picks the dataset-JSON entry / config
  file / log name via a `case` block.

## Decisions made (in this conversation)

| Question                                  | Decision                                                                                                                                                         |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Site rollout order                        | BNL, SLAC, NERSC in parallel, not sequential                                                                                                                     |
| RNTuple file provenance at BNL/SLAC/NERSC | Convert locally at each site from its own already-downloaded TTree ntuples, via that site's own batch system — not transferred in from UC via Rucio or otherwise |
| StatAnalysis bump scope                   | Both FastFrames and EventLoop move to 0.7.3 at all three sites (not FastFrames-only)                                                                             |
| Python 3.13 scope                         | coffea only, at all 5 sites. FastFrames/EventLoop are not in scope for this (constrained by StatAnalysis's bundled Python; see Constraints)                      |

## Open items / first validation steps (not yet checked)

1. **Confirm EventLoop's RNTuple reading actually works under StatAnalysis
   0.7.3** before wiring it into any site's crontab/scrontab — open one of UC's
   already-converted RNTuple files with a throwaway script under
   `asetup StatAnalysis,0.7.3` and confirm it doesn't crash (the segfault
   workaround in UC's code suggests this genuinely needs checking, not
   assuming).
2. **Confirm what Python 3.13 build is actually available via ALRB's
   `lsetup python`** at each site (e.g. `lsetup python -h` or `showVersions`) —
   the existing `lsetup 'python 3.9.22-x86_64-el9'` pattern implies a specific
   build string is needed, not a bare "3.13".
3. **Confirm coffea's pip-installed stack (awkward/uproot/coffea) is compatible
   with Python 3.13** at each site before flipping the version — this is a
   separate compatibility question from the StatAnalysis one.

## What's left to the builder

- The exact per-site paths for each site's RNTuple dataset copy (mirroring how
  each site's existing one-time-setup table documents its own TTree dataset
  location) — pull these from each site's own `docs/<site>/benchmarks.md`
  one-time-setup section rather than assuming UC's paths apply.
- The SLAC/NERSC Slurm equivalent of `convert.sub` (array job vs. submit-loop is
  a builder's call; either is fine as long as it's resumable — UC's
  `convert_job.sh` already skips inputs whose output exists, so resubmitting a
  partial list is safe either way).
- BNL's HTCondor equivalent — should follow the same `.sub`-per-file-list
  pattern UC already uses, adapted for BNL's existing HTCondor conventions (see
  `TRUTH3/BNL/EL9/cron_el_batch.sh` and siblings for the house style).
- The exact `-rntuple` crontab/scrontab entries for each site — 4 new job types
  (coffea, eventloop-columnar, eventloop-standard, fastframes) × 3 sites = 12
  new scheduled entries, following the existing per-site pattern (BNL: new cron
  lines calling the existing per-job wrapper with a format arg; SLAC: new
  entries exec'ing into the shared `parsing/utils/submit_and_upload.sh`, same
  shape as SLAC's existing jobs; NERSC: new `#SCRON`-decorated lines in
  `crontab_nersc.txt` calling that same shared script with the rntuple log
  name).
- Whether to fold the `benchmark_utils.sh` duplication finding from the #93/#91
  code review (split.log-clear + failure-classification logic copy-pasted into
  NERSC's `run_*.sh` scripts) into a shared helper while touching these same
  files for the version bump — builder's call; not required for this project's
  goals, but touching the same files is a reasonable moment to do it if it's
  cheap.
- Docs: new sections in `docs/bnl/benchmarks.md`, `docs/slac/benchmarks.md`,
  `docs/nersc/benchmarks.md` for the RNTuple jobs and the version bump
  (mirroring `docs/uchicago/benchmarks.md`'s "RNTuple twin" framing), and a note
  in `docs/workflows/rntuple-conversion.md` that it now also runs independently
  at BNL/SLAC/NERSC against their own ntuple copies, not just at UC.

## Testing / validation approach

Same pattern as the SLAC and NERSC account migrations: Qi runs each step live
over SSH at each site and reports back (pasted terminal output); no direct
machine access from this session. Validate each site independently before
considering that site's rollout done — a green result at one site doesn't imply
the others will behave the same, given the sites differ in batch system
(HTCondor/Slurm), filesystem, and (per the open items above) possibly in
RNTuple-reading behavior under the shared StatAnalysis version.
