# SLAC Benchmark Pipeline

**Schedule:** `CrontabFiles/crontab_slac.txt`

Like BNL, SLAC has no GitHub Actions workflow behind it — every benchmark job
runs via a `cron` entry that submits to Slurm instead of HTCondor. SLAC's
crontab lives on a different host than the Slurm submit host (`iana`), so every
cron entry is a thin `ssh iana ...` wrapper into a per-job
`submit_and_upload.sh` alongside each job's Slurm submission script. That
per-job script only handles what's genuinely SLAC-specific (the overlap lock,
the `cd`, and for TRUTH3/EVNT a clean of the job's scratch directory) and then
`exec`s into the same shared, site-neutral `parsing/utils/submit_and_upload.sh`
that [NERSC](../nersc/benchmarks.md) uses, which does the actual
submit-wait-locate-parse-upload work.

## Trigger

The pipeline runs:

- **Every 6 hours** (cron schedule: `0 */6 * * *`)

As with BNL, there's no pull-request trigger and no manual dispatch equivalent —
those are GitHub Actions concepts, and SLAC has no CI system in the loop.

## Benchmark Jobs

The crontab runs 11 jobs, all on the same 6-hour cadence. Cron itself runs each
job's `cron_*.sh` `ssh` wrapper; the Script column is what that wrapper runs on
`iana`:

| Job                          | Script                                                            | Log File                  | Description                                        |
| ---------------------------- | ----------------------------------------------------------------- | ------------------------- | -------------------------------------------------- |
| `rucio`                      | `./Rucio/cron_rucio_slac.sh` (→ `rucio_script.sh`'s `slac)` case) | `rucio.log`               | Download data using Rucio                          |
| `evnt-el9`                   | `./EVNT/SLAC/EL9/submit_and_upload.sh`                            | `log.generate`            | EVNT generation (EL9 container, batch)             |
| `evnt-centos7`               | `./EVNT/SLAC/CentOS7/submit_and_upload.sh`                        | `log.generate`            | EVNT generation (CentOS7 container, batch)         |
| `truth3-el9`                 | `./TRUTH3/SLAC/EL9/submit_and_upload.sh`                          | `log.Derivation`          | TRUTH3 derivation (EL9 container, batch)           |
| `truth3-el9-interactive`     | `./TRUTH3/SLAC/EL9_i/run_truth3_el9_interactive.sh`               | `log.Derivation`          | TRUTH3 derivation (EL9 container, interactive)     |
| `truth3-centos7`             | `./TRUTH3/SLAC/CentOS7/submit_and_upload.sh`                      | `log.EVNTtoDAOD`          | TRUTH3 derivation (CentOS7 container, batch)       |
| `truth3-centos7-interactive` | `./TRUTH3/SLAC/CentOS7_i/run_truth3_centos7_interactive.sh`       | `log.EVNTtoDAOD`          | TRUTH3 derivation (CentOS7 container, interactive) |
| `coffea`                     | `./NTuple_Hist/coffea/SLAC/submit_and_upload.sh`                  | `coffea_hist.log`         | NTuple to histogram (Coffea)                       |
| `fastframes`                 | `./NTuple_Hist/fastframes/SLAC/submit_and_upload.sh`              | `fastframes.log`          | NTuple to histogram (FastFrames)                   |
| `eventloop-columnar`         | `./NTuple_Hist/event_loop/SLAC/columnar/submit_and_upload.sh`     | `event_loop_arrays.log`   | Event loop (columnar)                              |
| `eventloop-standard`         | `./NTuple_Hist/event_loop/SLAC/standard/submit_and_upload.sh`     | `event_loop_noarrays.log` | Event loop (standard)                              |

## Workflow Steps

Each `sbatch`-based job follows this pattern:

1. **Cron trigger** — `cron` fires the one-line `ssh iana ...` wrapper every 6
   hours
2. **Lock and clean** — the job's own `submit_and_upload.sh` takes the
   non-blocking `flock` guard and `cd`s into the job directory (TRUTH3 and EVNT
   also empty it), then `exec`s into the shared
   `parsing/utils/submit_and_upload.sh`
3. **Submit** — the shared script exports `SUBMIT_TIME` and calls
   `sbatch --wait --parsable`, which queues the job on Slurm and blocks until it
   finishes. A job that exits non-zero is still parsed and uploaded if it wrote
   an output directory
4. **Execute** — Slurm runs the job inside an ALRB container on a compute node,
   which does the actual work and calls `append_benchmark` (the same
   `benchmark_utils.sh` helper every site's scripts use) once at the end
5. **Locate output** — once `sbatch --wait` returns, the shared script globs for
   output directories newer than a marker it set before submitting (Slurm gives
   no direct equivalent of HTCondor's per-cluster log path, and the marker stops
   a crashed run from re-uploading the previous run's result)
6. **Parse** — the shared script calls `parsing/utils/parse_upload.sh`, which
   runs `python -m parsing.scripts.ci_parse` — the same script the `parse`
   composite action wraps on UChicago (see
   [parsing and upload](../workflows/parsing.md))
7. **Upload to Kibana** — `parse_upload.sh` `curl`s the payload to LogStash —
   the same mechanism the `upload` action wraps

Two things don't fit this pattern:

- **Rucio** and the two **interactive TRUTH3** jobs run synchronously on `iana`
  itself (no `sbatch`/compute node involved), so there's no submit-wait-locate
  step. Rucio calls `parse_upload.sh` once the container returns; the
  interactive TRUTH3 scripts run `ci_parse` and `curl` inline.
- Because the parse step always runs on `iana`, but an `sbatch`-based job ran on
  a different Slurm compute node, `$(hostname)` at parse time would report
  `iana`, not the node that did the work. Every `sbatch`-based job writes
  `hostname.txt` into its output directory from inside the job itself, and
  `parse_upload.sh` reads that file back — falling back to `$(hostname)` if it's
  absent, which is already correct for Rucio/interactive since those run on
  `iana` directly.

### Example Job Structure

Using TRUTH3 EL9 as the concrete example. The cron entry is a one-line `ssh`
wrapper, `TRUTH3/SLAC/EL9/cron_truth3_el9_batch.sh`:

```bash
#!/bin/bash

# Submission, waiting for completion, parsing, and uploading all happen in
# submit_and_upload.sh on iana (the Slurm submit host) -- see that file for
# why this is a single script rather than a multi-line ssh block.
# Keepalives are needed because this ssh session blocks for the job's full
# walltime.
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana \
  /sdf/home/q/qlei/AF-Benchmarking/TRUTH3/SLAC/EL9/submit_and_upload.sh
```

`TRUTH3/SLAC/EL9/submit_and_upload.sh` handles the SLAC-specific overlap guard
and cleanup, then hands off to the shared script:

```bash
#!/bin/bash
# Runs entirely on iana (the Slurm submit host): submits the TRUTH3 EL9
# batch job, blocks until it finishes, then parses and uploads the result.
# Mirrors TRUTH3/BNL/EL9/cron_el_batch.sh, with sbatch --wait standing in
# for condor_submit + condor_wait.

set -uo pipefail

readonly AF_BENCH_DIR="/sdf/home/q/qlei/AF-Benchmarking"

readonly job_dir="/sdf/home/q/qlei/TRUTH3Job/container_el"
readonly sub_file="${AF_BENCH_DIR}/TRUTH3/SLAC/EL9/truth3_el9_sub.sh"
readonly log_base="/sdf/data/atlas/u/qlei/benchmarks"
readonly log_output="log.Derivation"
readonly job_output_name="TRUTH3_el9_container"

readonly pixi_job="truth3"
readonly pixi_log_type="truth3"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="true"

# Prevent a second cron-triggered run from racing this one: sbatch --wait
# blocks for the job's full walltime, so if a run is still active past the
# next 6-hour cron firing, an unguarded rm -rf below would delete the
# still-running job's working directory out from under it.
readonly lock_file="${job_dir}.lock"
exec 200>"${lock_file}"
if ! flock -n 200; then
  echo "ERROR: another instance of this job is already running (lock: ${lock_file}) -- exiting without touching ${job_dir}"
  exit 1
fi

# Clean the job's scratch directory before submitting, same as the old
# fire-and-forget wrapper did.
cd "${job_dir}" || { echo "ERROR: could not cd into ${job_dir}"; exit 1; }
rm -rf ./*

# The shared wrapper submits, waits, picks this run's output directory and
# uploads it. exec keeps fd 200 open, so the lock is held until it exits.
exec "${AF_BENCH_DIR}/parsing/utils/submit_and_upload.sh" \
  --sub-file "${sub_file}" \
  --output-glob "${log_base}/*/${job_output_name}" \
  --log-name "${log_output}" \
  --cluster "SLAC-AF" \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --os "${pixi_os}" \
  --mode "${pixi_mode}" \
  --containerized "${pixi_containerized}"
```

`parsing/utils/submit_and_upload.sh` is the shared, site-neutral script every
`sbatch`-based job on both SLAC and NERSC `exec`s into (an abridged copy is on
[NERSC's page](../nersc/benchmarks.md#example-job-structure)). It exports
`SUBMIT_TIME`, submits `--sub-file` with `sbatch --wait`, globs `--output-glob`
for directories newer than a marker it set beforehand, and calls
`parse_upload.sh` with the newest match.

`truth3_el9_sub.sh` is the Slurm submission script it calls — it launches the
ALRB container and points its payload at `run_truth3_el9_container.sh`:

```bash
#!/bin/bash
# shellcheck disable=SC1091
#
#SBATCH --account=atlas:usatlas
#SBATCH --partition=ampere
#SBATCH --gpus a100:0
#SBATCH --job-name=truth3_batch
#SBATCH --output=output-%j.txt
#SBATCH --error=output-%j.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=3g
#SBATCH --time=0-00:30:00

unset KRB5CCNAME

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Use ALRB_CONT_CMDOPTS to provide bind mount, etc. options

export ALRB_CONT_CMDOPTS="-B /sdf"

export ALRB_CONT_RUNPAYLOAD="source /sdf/home/q/qlei/AF-Benchmarking/TRUTH3/SLAC/EL9/run_truth3_el9_container.sh"

# ALRB runs the payload in a clean environment (apptainer exec -e), so the
# SUBMIT_TIME that submit_and_upload.sh exports would not reach
# append_benchmark; apptainer sets APPTAINERENV_<NAME> as <NAME> inside.
# Empty when the job is submitted without the wrapper.
export APPTAINERENV_SUBMIT_TIME="${SUBMIT_TIME:-}"

# shellcheck disable=SC1091
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh -c el9
```

The `APPTAINERENV_SUBMIT_TIME` export is what gives SLAC a real `queueTime`:
`append_benchmark` writes `submit_time_utc` from `SUBMIT_TIME`, and without the
export it would be empty inside the container. All 8 SLAC submission scripts
have it; a job submitted by hand with `sbatch` reports no submit time.

And `run_truth3_el9_container.sh` is where the actual workload runs, inside the
container, ending with the same `append_benchmark` call every site uses
(comments omitted):

```bash
#!/bin/bash

# shellcheck disable=SC1091
source /sdf/home/q/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log

setup_start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
asetup Athena,24.0.53,here
setup_end=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

set_time_cmd

"${TIME_CMD[@]}" Derivation_tf.py --CA True --inputEVNTFile /sdf/data/atlas/u/qlei/TRUTH3Files/el/EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

# time -v's report lands in the tee'd pipe, not in Derivation_tf.py's own
# log.Derivation -- fold it in so append_benchmark can read it.
cat pipe_file.log >> log.Derivation

date -u "+%Y-%m-%dT%H:%M:%SZ" >> split.log
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

output_dir="/sdf/data/atlas/u/$USER/benchmarks/${curr_time}/TRUTH3_el9_container"
mkdir -p "${output_dir}"
hostname >> split.log
du DAOD_TRUTH3.TRUTH3.root >> split.log

# The parse step runs on iana, a different host than the compute node
# that ran this job -- $(hostname) at parse time would report iana, not
# the ampere node. Record the real one here instead.
hostname > "${output_dir}/hostname.txt"

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "${bench_mode}"

mv log.Derivation "${output_dir}"
mv split.log "${output_dir}"
mv pipe_file.log "${output_dir}"
```

This same shape — a one-line `ssh` wrapper, a per-job `submit_and_upload.sh`
that `exec`s into the shared one, a Slurm submission script, and a payload
script — is used by the other 7 `sbatch`-based jobs. The names vary: the
submission scripts are `*_sub.sh` except EventLoop's `event_loop_arrays.sh` and
`event_loop_noarrays.sh`, and the NTuple payloads are `run_example.sh`,
`run_fastframes.sh` and `run_eventloop_{arrays,noarrays}.sh` rather than
`run_*_container.sh`. Besides the path constants, the `--output-glob`/
`--log-name` and `--job`/etc. arguments, and the workload, the wrappers differ
only in whether they empty the job directory (TRUTH3 and EVNT do).
`set_time_cmd` is a shared helper in `parsing/utils/benchmark_utils.sh`, used by
all 8 payloads to avoid duplicating the same `/usr/bin/time` availability check.
`parsing/tests/test_slac_wrappers.py` checks the lock, the cleanup and the
`SUBMIT_TIME` forwarding.

## Monitoring Results

### Viewing Job Runs

- **Output directories:**
  `/sdf/data/atlas/u/qlei/benchmarks/<timestamp>/<output name>/`, where the
  output name is the payload's directory name (`TRUTH3_el9_container`,
  `Coffea_Hist`, `eventloop_arrays`, ...), not the job name. Rucio writes to
  `$HOME/af_benchmarking/rucio/logs/<timestamp>/` instead. There's no GitHub
  Actions UI equivalent; check the filesystem directly
- **Slurm status:** `squeue -u qlei` while a job is queued or running

### Checking Logs

- **Slurm output:** `output-<jobid>.txt` in the job's scratch directory (set by
  `#SBATCH --output`/`--error` in the `*_sub.sh` file)
- **Benchmark logs:** the job's own log file (e.g. `log.Derivation`), moved into
  the output directory once the job completes

### Common Issues

**Benchmark job failures:**

- Check the Slurm `output-<jobid>.txt` file for the job
- The wrappers write no log file of their own: their output goes to the cron
  `ssh` session. To see it, run the job's `cron_*.sh` by hand
- `WARNING: job <id> exited <status>; uploading whatever it wrote` means the job
  failed but its result was still uploaded; `ERROR: sbatch submission failed`
  and `ERROR: no new output directory matches <glob>` mean nothing was uploaded
- Review the job's log file for script errors

**Overlapping runs:**

- `ERROR: another instance of this job is already running (lock: ...)` means a
  previous run's `sbatch --wait` is still blocking past the next 6-hour cron
  firing — the non-blocking `flock` guard in `submit_and_upload.sh` exits rather
  than letting a second run race the first and corrupt a shared working
  directory

**Parsing failures:**

- Check that the log file contains a `=== BENCHMARK ===` block
- Verify the payload validates against the schema
- Check `KIBANA_TOKEN`/`KIBANA_URI` are set (sourced from `~/.secrets`)

**Upload failures:**

- Verify `payload.json` was generated by the parse step; `parse_upload.sh`
  writes it, and the server's reply as `response.txt`, into the output directory
  (readable only by `qlei`)
- Check the HTTP response status printed by `parse_upload.sh`; the upload gives
  up after 60 seconds
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
