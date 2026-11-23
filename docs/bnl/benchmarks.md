# BNL Benchmark Pipeline

**Schedule:** `CrontabFiles/crontab_bnl.txt`

Unlike UChicago, BNL has no GitHub Actions workflow behind it — every benchmark
job runs via a plain `cron` entry on the BNL login node, submitting to HTCondor
directly. There is no equivalent of `uchicago.yml`; the entire pipeline lives in
shell scripts checked into this repo and a crontab installed on the host.

## Trigger

The pipeline runs:

- **Every 6 hours** (cron schedule: `0 */6 * * *`). The four `-rntuple` jobs
  start half an hour later (`30 */6 * * *`), so the two formats do not compete
  for the same GPFS and CPUs while they are being measured.

There's no pull-request trigger and no manual dispatch equivalent — those are
GitHub Actions concepts, and BNL has no CI system in the loop.

## Benchmark Jobs

The crontab runs 15 jobs, all on a 6-hour cadence:

| Job                          | Script                                                                    | Log File                         | Description                               |
| ---------------------------- | ------------------------------------------------------------------------- | -------------------------------- | ----------------------------------------- |
| `rucio`                      | `./Rucio/rucio_script.sh` (via `cron_rucio_bnl.sh`)                       | `rucio.log`                      | Download data using Rucio                 |
| `evnt-native`                | `./EVNT/BNL/Native/run_evnt_native_batch.sh`                              | `log.generate`                   | EVNT generation (native)                  |
| `evnt-el9`                   | `./EVNT/BNL/EL9/run_evnt_el9_batch.sh`                                    | `log.generate`                   | EVNT generation (EL9 container)           |
| `evnt-centos7`               | `./EVNT/BNL/CentOS7/run_evnt_centos7_batch.sh`                            | `log.generate`                   | EVNT generation (CentOS7 container)       |
| `truth3-native`              | `./TRUTH3/BNL/Native/run_truth3_native_batch.sh`                          | `log.Derivation`                 | TRUTH3 derivation (native)                |
| `truth3-el9`                 | `./TRUTH3/BNL/EL9/run_truth3_el9_batch.sh`                                | `log.Derivation`                 | TRUTH3 derivation (EL9 container)         |
| `truth3-centos7`             | `./TRUTH3/BNL/CentOS7/run_truth3_centos7_batch.sh`                        | `log.EVNTtoDAOD`                 | TRUTH3 derivation (CentOS7 container)     |
| `coffea`                     | `./NTuple_Hist/coffea/BNL/run_example.sh`                                 | `coffea_hist.log`                | NTuple to histogram (Coffea)              |
| `eventloop-columnar`         | `./NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh`           | `eventloop_arrays.log`           | Event loop (columnar)                     |
| `eventloop-standard`         | `./NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh`         | `eventloop_noarrays.log`         | Event loop (standard)                     |
| `fastframes`                 | `./NTuple_Hist/fastframes/BNL/run_fastframes.sh`                          | `fastframes.log`                 | NTuple to histogram (FastFrames)          |
| `coffea-rntuple`             | `./NTuple_Hist/coffea/BNL/run_example.sh rntuple`                         | `coffea_hist_rntuple.log`        | NTuple to histogram (Coffea, RNTuple)     |
| `eventloop-columnar-rntuple` | `./NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh rntuple`   | `eventloop_arrays_rntuple.log`   | Event loop (columnar, RNTuple)            |
| `eventloop-standard-rntuple` | `./NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh rntuple` | `eventloop_noarrays_rntuple.log` | Event loop (standard, RNTuple)            |
| `fastframes-rntuple`         | `./NTuple_Hist/fastframes/BNL/run_fastframes.sh rntuple`                  | `fastframes_rntuple.log`         | NTuple to histogram (FastFrames, RNTuple) |

The four `-rntuple` jobs are twins of the jobs above them; see
[RNTuple variants](#rntuple-variants).

## Workflow Steps

Each job follows this pattern:

1. **Cron trigger** - `cron` fires the wrapper script every 6 hours
2. **Submit** - `condor_submit` queues the job on HTCondor
3. **Wait** - `condor_wait` blocks until the job finishes
4. **Execute** - HTCondor runs the job executable, which does the actual work
   and calls `append_benchmark` (the same `benchmark_utils.sh` helper every
   site's scripts use) once at the end
5. **Parse** - the cron wrapper runs `python -m parsing.scripts.ci_parse`
   directly — the same script the `parse` composite action wraps on UChicago
   (see [parsing and upload](../workflows/parsing.md))
6. **Upload to Kibana** - the cron wrapper `curl`s the payload to LogStash — the
   same mechanism the `upload` action wraps

### Example Job Structure

Using `TRUTH3/BNL/Native/cron_native_batch.sh` as the concrete example:

```bash
#!/bin/bash

# Configuration
readonly log_base="/atlasgpfs01/usatlas/data/qlei/logs/TRUTH3_native_batch"
readonly log_output="log.Derivation"
readonly job_dir="/usatlas/u/qlei/test/TRUTH3/native"
readonly AF_BENCH_DIR="/usatlas/u/qlei/AF-Benchmarking"
readonly sub_file="${AF_BENCH_DIR}/TRUTH3/BNL/Native/truth3_native.sub"

readonly pixi_job="truth3"
readonly pixi_log_type="truth3"
readonly pixi_os="alma9"
readonly pixi_mode="batch"
readonly pixi_containerized="false"

export PATH="/usatlas/u/qlei/.pixi/bin:$PATH"
[ -r /usatlas/u/qlei/.secrets ] && . /usatlas/u/qlei/.secrets

submit_out=$(condor_submit "${sub_file}")
cluster_id=$(echo "${submit_out}" | grep -oP '(?<=cluster )\d+')

log_template=$(grep -i '^log' "${sub_file}" | awk '{print $NF}')
condor_log="${log_template//\$(Cluster)/${cluster_id}}"
condor_log="${condor_log//\$(Process)/0}"

condor_wait "${condor_log}" || { echo "ERROR: condor_wait failed"; exit 1; }

latest_dir=$(find "${log_base}" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')

pixi run --manifest-path "${AF_BENCH_DIR}/pixi.toml" -e kibana python -m parsing.scripts.ci_parse \
  --job "${pixi_job}" \
  --log-type "${pixi_log_type}" \
  --log-file "${latest_dir}/${log_output}" \
  --cluster "BNL-AF" \
  --token="${KIBANA_TOKEN}" \
  --kind="benchmark" \
  --host="$(hostname)" \
  --os="${pixi_os}" \
  --mode="${pixi_mode}" \
  --containerized="${pixi_containerized}" \
  --output="${latest_dir}/payload.json"

response=$(curl -X POST "${KIBANA_URI}" \
  -H "Content-Type: application/json" \
  -d @"${latest_dir}/payload.json" \
  -w "%{http_code}" \
  -s -o "${job_dir}/response.txt")
```

This same ~94-line skeleton — only the path constants and the four `pixi_*`
variables change — is used by all 11 BNL cron wrappers.

The `.sub` file it submits is minimal — `Universe = vanilla`, a fixed
`request_memory`, and `Queue 1`:

```
Universe = vanilla

Output = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).out
Error = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).err
Log = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).log

Executable = /usatlas/u/qlei/AF-Benchmarking/TRUTH3/BNL/Native/run_truth3_native_batch.sh

request_memory = 3G

Queue 1
```

## One-Time Setup

None of this lives in the repo. It has to exist on the BNL login node before the
crontab can run:

| What                    | Where                                                                                                                                                                                       | Notes                                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repo checkout           | `~/AF-Benchmarking` (`/usatlas/u/qlei/AF-Benchmarking`)                                                                                                                                     | Exact path: the `.sub` files and cron wrappers use it. Check out the branch the crontab should run                                                            |
| Kibana credentials      | `~/.secrets`                                                                                                                                                                                | Exports `KIBANA_TOKEN`/`KIBANA_URI`; never committed                                                                                                          |
| pixi                    | `~/.pixi/bin`                                                                                                                                                                               | Used by the cron wrappers' parse step                                                                                                                         |
| ALRB local config       | `~/localConfig`                                                                                                                                                                             | Used as `ALRB_localConfigDir` by the container jobs                                                                                                           |
| Cron job directories    | `/usatlas/u/qlei/test/<job>` for `coffea`, `eventloop_arrays`, `eventloop_noarrays`, `fastframes` and each one's `_rntuple` twin                                                            | Must exist: a wrapper stops with `job_dir does not exist`. Each wrapper empties its directory when it finishes                                                |
| HTCondor output dirs    | `/usatlas/u/qlei/batch_output_files/{coffea,eventloop,eventloop_arrays,fastframes,convert}/`                                                                                                | The `.sub` files write their `.out`/`.err`/`.log` here; create them before the first run                                                                      |
| Job working directories | `/atlasgpfs01/usatlas/data/qlei/ntuple/{coffea,eventloop_arrays,eventloop_noarrays}` and `/atlasgpfs01/usatlas/data/qlei/fastframes_rntuple`, each with an `_rntuple` twin where it applies | Created by the scripts. Each format has its own, so overlapping runs cannot clobber each other                                                                |
| Input ntuples (TTree)   | `/atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/`                                                                                             | Another user's directory, readable but not writable by `qlei`                                                                                                 |
| Input ntuples (RNTuple) | `/atlasgpfs01/usatlas/data/qlei/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS_RNTuple.root/`                                                                                          | Written once by the conversion job, see [below](#converting-the-dataset-to-rntuple)                                                                           |
| coffea dataset JSONs    | TTree: `/atlasgpfs01/usatlas/data/jroblesgo/single_campaign_mc20e_dataset_runnable/af_v2_700402.json`. RNTuple: `NTuple_Hist/coffea/BNL/single_campaign_mc20e_dataset_runnable/`            | The TTree one is hardcoded in `example.py`. `run_example.sh` copies the RNTuple one into the working directory                                                |
| FastFrames inputs       | `/atlasgpfs01/usatlas/data/qlei/input/`                                                                                                                                                     | The TTree job's config, file list and sum-of-weights file, kept by hand and seen in the container as `/srv/input`. The RNTuple job's are copied from the repo |
| FastFrames build        | `/atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3/`                                                                                                                                  | See [below](#building-fastframes-72). CMake caches absolute paths, so a build directory cannot be copied between machines                                     |

### Building FastFrames 7.2

FastFrames reads RNTuple from version 7.0, and 7.2.0 needs `StatAnalysis,0.7.3`.
`NTuple_Hist/fastframes/BNL/build_fastframes.sh` is the site-generic script that
builds FastFrames and then the `TutorialClass` custom frame against it. Run it
on a compute node, not the login node (the C++ templates in RDataFrame code can
need several GB per compiler process):

```bash
FF=/atlasgpfs01/usatlas/data/qlei/FastFramesTutorial_0.7.3
mkdir -p $FF
git clone --branch v7.2.0 https://gitlab.cern.ch/atlas-amglab/fastframes.git $FF/FastFrames
# reuse the TutorialClass source from an earlier tutorial tree, without its build/install
rsync -a --exclude build --exclude install <old tree>/TutorialClass/ $FF/TutorialClass/
FF_DIR=$FF JOBS=4 bash NTuple_Hist/fastframes/BNL/build_fastframes.sh
```

The build is good when its last line lists `libTutorialClass.so`. A
`TutorialClass` source written for FastFrames 6.0.0 compiled against 7.2.0
unchanged.

### Converting the dataset to RNTuple

The jobs read an RNTuple copy of the dataset, made once with
`NTuple_Hist/rntuple_conversion/BNL/convert.sub` (one HTCondor job per file in
`inputs.txt`) and `NTuple_Hist/rntuple_conversion/UC/convert_job.sh`, which the
sites share. See
[TTree to RNTuple Conversion](../workflows/rntuple-conversion.md) for how the
conversion works.

```bash
mkdir -p /usatlas/u/qlei/batch_output_files/convert
cd NTuple_Hist/rntuple_conversion/BNL && condor_submit convert.sub
```

At UC the RNTuple copy sits next to the original. At BNL the original dataset
belongs to another user and is not writable, so `convert.sub` passes
`convert_job.sh` an output directory under `/atlasgpfs01/usatlas/data/qlei`
instead. Each job checks its own file (entry counts, every column) and prints an
`OK ...` line; all 18 files passed.

### The coffea environment

`run_example.sh` builds a Python 3.13 virtual environment in the job's working
directory with `lsetup 'python 3.13.18-x86_64-el9'`. It installs `atlas_schema`
below 0.5 and `dask_histogram` explicitly:

- `atlas_schema` 0.5.0 gives every photon a default `mass` next to the ntuple's
  own `e` branch, and coffea's Lorentz-vector validation rejects that
  (`multiple temporal aliases present`).
- coffea 2026.11 no longer installs `dask_histogram`, which `example.py` needs
  (`import hist.dask`).

The environment is built once and `pip install` leaves existing packages alone,
so it keeps whatever versions it was first built with. Delete
`/atlasgpfs01/usatlas/data/qlei/ntuple/coffea/venv` (and the `coffea_rntuple`
one) to rebuild it.

## Monitoring Results

### Viewing Job Runs

- **Output directories:**
  `/atlasgpfs01/usatlas/data/qlei/logs/<job>/<timestamp>/` — no GitHub Actions
  UI equivalent; check the filesystem directly
- **HTCondor status:** `condor_q` while a job is queued or running

### Checking Logs

- **HTCondor logs:** the `.out`/`.err`/`.log` files at the paths set in the
  `.sub` file's `Output`/`Error`/`Log` fields
- **Benchmark logs:** the job's own log file (e.g. `log.Derivation`), moved into
  the output directory once the job completes

### Common Issues

**Benchmark job failures:**

- Check the HTCondor `.err` file for the job
- Verify `condor_submit`/`condor_wait` succeeded in the cron wrapper's own
  output
- Review the job executable's log for script errors

**Parsing failures:**

- Check that the log file contains a `=== BENCHMARK ===` block
- Verify the payload validates against the schema
- Check `KIBANA_TOKEN`/`KIBANA_URI` are set (sourced from `~/.secrets`)

**A run that failed still uploads:**

- A cron wrapper parses and uploads whatever log the job left, so a failed run
  appears in Kibana with `status: 1`, and `HTTP Response Code: 200` says nothing
  about the run itself. Check `exit_status=` in the job's log and `status` in
  `payload.json`

**Upload failures:**

- Verify `payload.json` was generated by the parse step
- Check the HTTP response status printed by the cron wrapper
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

### RNTuple variants

The `coffea`, `eventloop-columnar`, `eventloop-standard` and `fastframes` jobs
each have an `-rntuple` twin that runs the same analysis on the RNTuple copy of
the same dataset (see
[TTree to RNTuple Conversion](../workflows/rntuple-conversion.md)), so the two
formats can be compared run for run. Each script takes the format as its first
argument (`ttree` by default), and the twins' `.sub` files pass `rntuple`. Each
format runs in its own working directory and writes its own log name and log
directory, so the two jobs never share files.

- **Coffea** runs the twin in virtual-array mode (`processor.Runner`) rather
  than the dask-awkward mode of the TTree job, because dask mode crashes on
  RNTuple input (the same reason as at UC, see the
  [UChicago page](../uchicago/benchmarks.md#rntuple-variants)).
- **EventLoop (columnar)** resolves each field once, as a token, and reads the
  entry with the tokens; **EventLoop (standard)** looks each field up by name on
  every event. They run under `StatAnalysis,0.7.3`, which ships ROOT 6.38, and
  use its reader API, which differs from UC's ROOT 6.34: `RNTupleReader` is no
  longer in `ROOT::Experimental`, PyROOT has no default entry, so the entry is
  made with `reader.CreateEntry()` and passed to every `LoadEntry`, and fields
  are read by indexing the entry.
- **FastFrames** runs 7.2.0 built against `StatAnalysis,0.7.3`. The RNTuple
  config differs from the TTree one only in its file list
  (`mc20e_filelist_rntuple.txt`).

All the jobs that use `StatAnalysis,0.7.3` run on its Python 3.10, which has no
`datetime.UTC` (Python 3.11+); the EventLoop payloads use
`datetime.timezone.utc` for that reason.

#### What the first runs showed

Run times from the first runs at BNL (2026-11-23), each reading all 18,304,905
events and writing the same histogram content (FastFrames' histograms matched
entry for entry and integral for integral):

| Job                  | TTree  | RNTuple | Note                                                                  |
| -------------------- | ------ | ------- | --------------------------------------------------------------------- |
| `coffea`             | 404 s  | 63 s    | dask-awkward against virtual-array mode: not a pure format comparison |
| `eventloop-columnar` | 710 s  | 1076 s  | the TTree job binds buffers once with `SetBranchAddress`              |
| `eventloop-standard` | 2849 s | 1084 s  | both read fields by name on every event                               |
| `fastframes`         | 323 s  | 172 s   |                                                                       |

The columnar EventLoop pair is the one where RNTuple is slower.
`SetBranchAddress` binds C++ buffers once and has almost no per-event cost, and
the RNTuple reader has no equivalent: every `entry[token]` call crosses into
Python for each event. Where both formats read fields by name per event (the
standard pair), RNTuple is about 2.6 times faster. The two formats' inputs are
also compressed differently (the RNTuple files are about 0.29 times the size),
so a size or I/O comparison is not a pure format comparison either; see the
[conversion page](../workflows/rntuple-conversion.md#what-to-expect). These are
single runs, so treat them as indicative.
