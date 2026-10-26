# NERSC Benchmark Pipeline

**Schedule:** `CrontabFiles/crontab_nersc.txt` (installed with `scrontab`)

Like BNL and SLAC, NERSC has no GitHub Actions workflow behind it. Instead of a
system `cron` on a dedicated host, NERSC uses
[`scrontab`](https://docs.nersc.gov/jobs/workflow/scrontab/), Slurm's own
cron-like interface, which runs directly on a Perlmutter login node. Every entry
calls the same shared, site-neutral `parsing/utils/submit_and_upload.sh` —
unlike BNL and SLAC, which each have their own per-job wrapper scripts, NERSC's
9 jobs are all just differently parameterized invocations of one script.

## Trigger

The pipeline runs:

- **Every 12 hours** (`0 */12 * * *`), on the `cron` QOS

As with BNL and SLAC, there's no pull-request trigger and no manual dispatch
equivalent — those are GitHub Actions concepts, and NERSC has no CI system in
the loop.

## Benchmark Jobs

`scrontab` runs 9 jobs, all on the same 12-hour cadence:

| Job                  | Sub File                                                            | Log File                 | Description                           |
| -------------------- | ------------------------------------------------------------------- | ------------------------ | ------------------------------------- |
| `rucio`              | `./Rucio/rucio_nersc_sub.sh`                                        | `rucio.log`              | Download data using Rucio             |
| `evnt-el9`           | `./EVNT/NERSC/EL9/evnt_el9_sub.sh`                                  | `log.generate`           | EVNT generation (EL9 container)       |
| `evnt-centos7`       | `./EVNT/NERSC/CentOS7/evnt_centos7_sub.sh`                          | `log.generate`           | EVNT generation (CentOS7 container)   |
| `truth3-el9`         | `./TRUTH3/NERSC/EL9/truth3_el9_sub.sh`                              | `log.Derivation`         | TRUTH3 derivation (EL9 container)     |
| `truth3-centos7`     | `./TRUTH3/NERSC/CentOS7/truth3_centos7_sub.sh`                      | `log.EVNTtoDAOD`         | TRUTH3 derivation (CentOS7 container) |
| `coffea`             | `./NTuple_Hist/coffea/NERSC/coffea_el9_sub.sh`                      | `coffea_hist.log`        | NTuple to histogram (Coffea)          |
| `fastframes`         | `./NTuple_Hist/fastframes/NERSC/fastframes_el9_sub.sh`              | `fastframes.log`         | NTuple to histogram (FastFrames)      |
| `eventloop-columnar` | `./NTuple_Hist/event_loop/NERSC/columnar/eventloop_arrays_sub.sh`   | `eventloop_arrays.log`   | Event loop (columnar)                 |
| `eventloop-standard` | `./NTuple_Hist/event_loop/NERSC/standard/eventloop_noarrays_sub.sh` | `eventloop_noarrays.log` | Event loop (standard)                 |

The `evnt`/`truth3` rows share a single `--job` value in Kibana (`evnt`,
`truth3`) — only the `os` field (`alma9` vs `centos7`) distinguishes the two
container variants there; the split rows above are for readability.

The two interactive TRUTH3 variants and the legacy photon eventloop job
(superseded by the columnar/standard jobs above) are present in the repo but
commented out in the crontab — the interactive scripts still point at the
previous account's paths and are not currently scheduled.

## Workflow Steps

Each job follows this pattern:

1. **`scrontab` trigger** — Slurm fires `parsing/utils/submit_and_upload.sh` on
   the login node every 12 hours, with the job's `--sub-file`, `--output-glob`,
   and `--cluster`/`--job`/`--os`/`--mode`/etc. metadata passed as arguments
2. **Submit** — `sbatch --wait --parsable` queues the job's `*_sub.sh` and
   blocks until it finishes; `--dependency=singleton` (one running instance per
   job name) stops a slow run from overlapping the next one
3. **Execute** — Slurm runs the job, which does the actual work inside an ALRB
   container and calls `append_benchmark` (the same `benchmark_utils.sh` helper
   every site's scripts use) once at the end
4. **Locate output** — `submit_and_upload.sh` globs `--output-glob` for
   directories newer than a marker it set before submitting, so a run that
   crashed before writing output can't cause the previous run's result to be
   re-uploaded
5. **Parse** — `submit_and_upload.sh` calls the shared
   `parsing/utils/parse_upload.sh`, which runs
   `python -m parsing.scripts.ci_parse` — the same script the `parse` composite
   action wraps on UChicago (see [parsing and upload](../workflows/parsing.md))
6. **Upload to Kibana** — `parse_upload.sh` `curl`s the payload to LogStash —
   the same mechanism the `upload` action wraps

Rucio runs through this same pattern rather than being a special case: its
`*_sub.sh` submits an `srun` of `Rucio/rucio_script.sh nersc`, which launches
its ALRB container synchronously and calls `append_benchmark` itself; once that
`sbatch --wait` returns, `submit_and_upload.sh` locates and uploads its log
exactly like every other job.

Because the parse step always runs on the login node, but the job itself ran on
a different Perlmutter compute node, `$(hostname)` at parse time would report
the login node, not the node that did the work. Every job writes `hostname.txt`
into its output directory from inside the job itself, and `parse_upload.sh`
reads that file back.

### Example Job Structure

The crontab entry for TRUTH3 EL9, from `CrontabFiles/crontab_nersc.txt`:

```
#SCRON -q cron
#SCRON -A m4956
#SCRON -J wrap_truth3_el9
#SCRON -t 12:00:00
#SCRON --dependency=singleton
#SCRON -o /global/cfs/cdirs/m2616/qlei/wrapper_logs/%x-%j.out
0 */12 * * * $HOME/AF-Benchmarking/parsing/utils/submit_and_upload.sh --sub-file $HOME/AF-Benchmarking/TRUTH3/NERSC/EL9/truth3_el9_sub.sh --output-glob "/global/cfs/cdirs/m2616/qlei/benchmarks/*/TRUTH3_el9_container" --log-name log.Derivation --cluster NERSC-AF --job truth3 --log-type truth3 --os alma9 --mode batch --containerized true
```

`parsing/utils/submit_and_upload.sh` is the one script every entry above calls,
parameterized entirely by its arguments:

```bash
#!/bin/bash
# Submits one Slurm benchmark job, waits for it to finish, then parses and
# uploads its log with parse_upload.sh. Meant to run on a login node (e.g.
# from scrontab), so the upload never depends on compute-node network access.
# Site-neutral: every site-specific value arrives as an argument.
#
# Usage: submit_and_upload.sh --sub-file S --output-glob G --log-name L \
#          --cluster C --job J --log-type T --os OS --mode M --containerized B
#
# --output-glob matches the per-run output directories the job writes, e.g.
# "/path/to/benchmarks/*/TRUTH3_el9_container"; quote it
# so the calling shell passes the pattern through. Of the directories created
# after submission, the newest is this run's output.
#
# A job that exits non-zero is still uploaded if it wrote an output directory;
# only a rejected submission (no job id) or a missing directory is an error.

set -uo pipefail

UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ... argument parsing omitted ...

# Anything newer than this marker was written by the job submitted below. It
# stops a run that crashed before creating its output directory from
# re-uploading the previous run's result.
marker=$(mktemp) || { echo "ERROR: mktemp failed" >&2; exit 1; }
trap 'rm -f "${marker}"' EXIT

# append_benchmark reads SUBMIT_TIME inside the job (sbatch passes the
# submitting environment through by default), which gives the parser a real
# queueTime.
SUBMIT_TIME=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
export SUBMIT_TIME

# scrontab sets SLURM_* variables that a child sbatch inherits and can fail
# on (https://docs.nersc.gov/jobs/workflow/scrontab/).
for var in $(compgen -e | grep '^SLURM_'); do
  unset "${var}"
done

job_id=$(sbatch --wait --parsable "${sub_file}")
# ... glob for new output dirs newer than the marker, then: ...

"${UTILS_DIR}/parse_upload.sh" \
  --cluster "${cluster}" \
  --job "${job}" \
  --log-type "${log_type}" \
  --log-file "${latest_dir}/${log_name}" \
  --os "${os}" \
  --mode "${mode}" \
  --containerized "${containerized}" \
  --output-dir "${latest_dir}"
```

`truth3_el9_sub.sh` is the Slurm submission script it calls:

```bash
#!/bin/bash

#SBATCH -N 1
#SBATCH -C cpu
#SBATCH -q shared
#SBATCH -A m4956
#SBATCH -J truth3_el9
#SBATCH --cpus-per-task=1
#SBATCH --constraint=cpu
#SBATCH -t 1:0:0
#SBATCH --mem=3G

export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

srun -n 1 -c 1 --cpu_bind=cores  "$HOME"/AF-Benchmarking/TRUTH3/NERSC/EL9/run_truth3_el9_batch.sh
```

And `run_truth3_el9_batch.sh` is where the actual workload runs. This is also
where [ALRB's `-r "<string>"` early-expansion bug](../workflows/parsing.md) had
to be designed around from the start: ALRB evaluates everything in that string
once, before any of it runs, so the script avoids runtime `$` entirely —
`date -u +SETUP_COMPLETE=...` prints its own label instead of being wrapped in
`$(date ...)`, and `/usr/bin/time -v` is called unguarded, since it's confirmed
present in both the `el9` and `centos7` containers here:

```bash
#!/bin/bash

# shellcheck disable=SC1091
source "$HOME"/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

job_dir="$SCRATCH/TRUTH3/el9/"
mkdir -p "${job_dir}"
cd "${job_dir}" || exit

# A run killed before its final mv leaves split.log behind; clear it so a
# stale SETUP_COMPLETE line cannot mask this run's failed setup.
rm -f split.log

cp ~/AF-Benchmarking/TRUTH3/EVNT.root .
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# ALRB evaluates the -r string once, before running any of it, so it holds
# no runtime $: date prints the SETUP_COMPLETE label itself rather than being
# wrapped in $(date). setup_end is written to split.log inside the container
# and read back after it exits.
# shellcheck disable=SC1091
source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -m /global/cfs/cdirs/m2616/qlei -r "asetup Athena,24.0.53,here && \
  date -u +SETUP_COMPLETE=%Y-%m-%dT%H:%M:%SZ >> split.log && \
  /usr/bin/time -v Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log && \
  cat pipe_file.log >> log.Derivation"

setup_end=$(grep "^SETUP_COMPLETE=" split.log 2>/dev/null | tail -1 | sed 's/^SETUP_COMPLETE=//')
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

output_dir="/global/cfs/cdirs/m2616/qlei/benchmarks/${curr_time}/TRUTH3_el9_container"
mkdir -p "${output_dir}"
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# The upload runs later on a login node, where $(hostname) would report the
# login node; record the compute node that ran the job.
hostname > "${output_dir}/hostname.txt"

# A failed release setup never reaches the payload, so there is no time -v
# report to read; record the failure explicitly instead.
bench_mode=time_v
[ -n "${setup_end}" ] || bench_mode=none

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
```

This same shape — a Slurm `*_sub.sh` and a `run_*_batch.sh` payload, driven by
the one shared `submit_and_upload.sh` — is used by the other 8 jobs; only the
path constants and the `submit_and_upload.sh` arguments change.

## One-Time Setup

None of this lives in the repo — it has to exist on Perlmutter before the
crontab can run:

| What                | Where                                              | Notes                                                                                                                                                                 |
| ------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repo checkout       | `~/AF-Benchmarking`                                | Exact name, case-sensitive — `scrontab` runs whatever is checked out here                                                                                             |
| Wrapper log dir     | `/global/cfs/cdirs/m2616/qlei/wrapper_logs/`       | Must exist, or Slurm silently drops wrapper output                                                                                                                    |
| Kibana credentials  | `~/.secrets`                                       | Exports `KIBANA_TOKEN`/`KIBANA_URI`; never committed                                                                                                                  |
| pixi                | `~/.pixi/bin`                                      | Used by `parse_upload.sh`; don't run `pixi lock` on Perlmutter                                                                                                        |
| ALRB local config   | `~/localConfig`                                    | Used as `ALRB_localConfigDir`                                                                                                                                         |
| Grid certificate    | `~/.globus/`                                       | `usercert.pem`/`userkey.pem` for the Rucio job's VOMS proxy                                                                                                           |
| Rucio password file | `~/af_benchmarking/rucio/pass.txt`                 | Read in the container as `/srv/pass.txt`; can be empty if the key has no passphrase                                                                                   |
| `$SCRATCH` job dirs | e.g. `$SCRATCH/EVNT/el9`, `$SCRATCH/ntuple/coffea` | Created once by hand; NERSC purges unused `$SCRATCH` files, so a job that starts failing with `no new output directory` after a quiet period may need these recreated |
| FastFrames build    | `/global/cfs/cdirs/m2616/qlei/FastFramesTutorial/` | Built on a compute node under `asetup StatAnalysis,0.6.2`; CMake caches absolute paths, so build directories can't be copied between machines                         |

/// note | FastFrames' `TutorialClass` build needs an explicit install prefix

Its `CMakeLists` defaults the install prefix to `""`, which writes `:/lib` into
`setup.sh` and makes the job fail with `Cannot get class TutorialClass`. Pass
`-DCMAKE_INSTALL_PREFIX=<path>/TutorialClass/install` explicitly when running
`cmake`.

///

## Monitoring Results

### Viewing Job Runs

- **Output directories:**
  `/global/cfs/cdirs/m2616/qlei/benchmarks/<timestamp>/<job>/` — no GitHub
  Actions UI equivalent; check the filesystem directly
- **Slurm status:** `squeue --me` — between cycles, expect 9 `wrap_*` jobs
  `PENDING` on a `BeginTime` hold

### Checking Logs

- **Wrapper logs:** `/global/cfs/cdirs/m2616/qlei/wrapper_logs/%x-%j.out` (one
  per `scrontab` firing)
- **Benchmark logs:** the job's own log file (e.g. `log.Derivation`), moved into
  the output directory once the job completes; Rucio's logs live under
  `~/af_benchmarking/rucio/logs/`

### Common Issues

**Checking for failures across all jobs:**

```bash
grep -H '^exit_status' */*/*.log | grep -v '=0$'
```

**Wrapper problems:**

```bash
grep -l -E 'ERROR|WARNING' /global/cfs/cdirs/m2616/qlei/wrapper_logs/wrap_*.out
```

**`ERROR: no new output directory matches ...`** — the job ran but wrote
nothing. Usually a transient failure (a grid proxy or Rucio hiccup) or a missing
`$SCRATCH` directory (see One-Time Setup above). Nothing is uploaded for that
cycle.

**Parsing failures:**

- Check that the log file contains a `=== BENCHMARK ===` block
- Verify the payload validates against the schema
- Check `KIBANA_TOKEN`/`KIBANA_URI` are set (sourced from `~/.secrets`)

**Upload failures:**

- Verify `payload.json` was generated by the parse step
- Check the HTTP response status printed by `parse_upload.sh`
- Verify `KIBANA_URI` is correct

## Benchmark Types Explained

### Rucio Download

Downloads ATLAS data files using the Rucio data management system. Measures data
transfer performance.

**Documentation:**
[Rucio Download Tutorial](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/rucio_download_files/)

### EVNT Generation

Generates Monte Carlo event files (EVNT format) using different runtime
environments.

**Documentation:**
[EVNT Production Tutorial](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/mc_generation/)

### TRUTH3 Derivation

Creates TRUTH3 derivation files from EVNT files for truth-level analysis.

**Documentation:**
[TRUTH3 Derivation Tutorial](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/mc_truth_derivation/)

### NTuple to Histogram

Converts NTuple ROOT files to histograms using various frameworks:

- **Coffea:** Python-based columnar analysis framework
- **FastFrames:** C++ framework for fast ROOT analysis
- **EventLoop:** Traditional ATLAS event processing framework
