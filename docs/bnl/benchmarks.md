# BNL Benchmark Pipeline

**Schedule:** `CrontabFiles/crontab_bnl.txt`

Unlike UChicago, BNL has no GitHub Actions workflow behind it — every benchmark
job runs via a plain `cron` entry on the BNL login node, submitting to HTCondor
directly. There is no equivalent of `uchicago.yml`; the entire pipeline lives in
shell scripts checked into this repo and a crontab installed on the host.

## Trigger

The pipeline runs:

- **Every 6 hours** (cron schedule: `0 */6 * * *`)

There's no pull-request trigger and no manual dispatch equivalent — those are
GitHub Actions concepts, and BNL has no CI system in the loop.

## Benchmark Jobs

The crontab runs 11 jobs, all on the same 6-hour cadence:

| Job                  | Script                                                            | Log File                 | Description                           |
| -------------------- | ----------------------------------------------------------------- | ------------------------ | ------------------------------------- |
| `rucio`              | `./Rucio/rucio_script.sh` (via `cron_rucio_bnl.sh`)               | `rucio.log`              | Download data using Rucio             |
| `evnt-native`        | `./EVNT/BNL/Native/run_evnt_native_batch.sh`                      | `log.generate`           | EVNT generation (native)              |
| `evnt-el9`           | `./EVNT/BNL/EL9/run_evnt_el9_batch.sh`                            | `log.generate`           | EVNT generation (EL9 container)       |
| `evnt-centos7`       | `./EVNT/BNL/CentOS7/run_evnt_centos7_batch.sh`                    | `log.generate`           | EVNT generation (CentOS7 container)   |
| `truth3-native`      | `./TRUTH3/BNL/Native/run_truth3_native_batch.sh`                  | `log.Derivation`         | TRUTH3 derivation (native)            |
| `truth3-el9`         | `./TRUTH3/BNL/EL9/run_truth3_el9_batch.sh`                        | `log.Derivation`         | TRUTH3 derivation (EL9 container)     |
| `truth3-centos7`     | `./TRUTH3/BNL/CentOS7/run_truth3_centos7_batch.sh`                | `log.EVNTtoDAOD`         | TRUTH3 derivation (CentOS7 container) |
| `coffea`             | `./NTuple_Hist/coffea/BNL/run_example.sh`                         | `coffea_hist.log`        | NTuple to histogram (Coffea)          |
| `eventloop-columnar` | `./NTuple_Hist/event_loop/BNL/columnar/run_eventloop_arrays.sh`   | `eventloop_arrays.log`   | Event loop (columnar)                 |
| `eventloop-standard` | `./NTuple_Hist/event_loop/BNL/standard/run_eventloop_noarrays.sh` | `eventloop_noarrays.log` | Event loop (standard)                 |
| `fastframes`         | `./NTuple_Hist/fastframes/BNL/run_fastframes.sh`                  | `fastframes.log`         | NTuple to histogram (FastFrames)      |

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
