# BNL Benchmark Pipeline

Unlike UChicago, BNL has no GitHub Actions workflow behind it — every benchmark
job runs via a plain `cron` entry on the BNL login node, submitting to HTCondor
directly. There is no equivalent of `uchicago.yml`; the entire pipeline lives in
shell scripts checked into this repo and a crontab installed on the host.

## Directory Layout

Each job type has a `BNL/` subdirectory, split by OS/container variant the same
way UChicago's are:

- `EVNT/BNL/{CentOS7,EL9,Native}/`
- `TRUTH3/BNL/{CentOS7,EL9,Native}/`, plus `{CentOS7,EL9,Native}_i/` interactive
  variants
- `Rucio/` — BNL doesn't have its own script; it shares `rucio_script.sh` with
  every other site, dispatched via a `bnl)` case branch
- `NTuple_Hist/{coffea,event_loop,fastframes}/BNL/`

## The Cron → HTCondor → Parse → Upload Pipeline

Every top-level cron entry point follows the same pattern: submit to HTCondor,
wait for it to finish, find the freshest output directory, parse the log, and
upload the payload — all in one script, since there's no CI system to hand any
of these steps off to.

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
```

It then submits the job, extracts the HTCondor cluster ID from `condor_submit`'s
output, and blocks on `condor_wait` for that specific job's log file:

```bash
submit_out=$(condor_submit "${sub_file}")
cluster_id=$(echo "${submit_out}" | grep -oP '(?<=cluster )\d+')

log_template=$(grep -i '^log' "${sub_file}" | awk '{print $NF}')
condor_log="${log_template//\$(Cluster)/${cluster_id}}"
condor_log="${condor_log//\$(Process)/0}"

condor_wait "${condor_log}" || { echo "ERROR: condor_wait failed"; exit 1; }
```

Once the job completes, it finds the most recently modified output directory,
then parses and uploads exactly the way the `parse`/`upload` composite actions
do on UChicago — just inlined instead of factored into a reusable action:

```bash
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
variables change — is used by all 11 BNL cron wrappers: EVNT
(CentOS7/EL9/Native), TRUTH3 batch (CentOS7/EL9/Native), Rucio, Coffea, and both
EventLoop variants.

## The Job Executable

The cron wrapper only orchestrates — it never sources
`parsing/utils/benchmark_utils.sh` itself. That happens one layer down, in the
actual job executable that HTCondor runs
(`TRUTH3/BNL/Native/run_truth3_native_batch.sh`):

```bash
#!/bin/bash
source /usatlas/u/qlei/AF-Benchmarking/parsing/utils/benchmark_utils.sh

start_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
# ... setup, asetup, Derivation_tf.py ...
end_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

append_benchmark log.Derivation "${start_time}" "${end_time}" "${setup_start}" "${setup_end}" "time_v"

mv log.Derivation "${output_dir}"
```

Every batch job executable at BNL follows this same split: the `.sub` file tells
HTCondor which executable to run, the executable does the actual work and calls
`append_benchmark` once at the end, and the cron wrapper (running outside
HTCondor, on the login node) picks up the result afterward.

## HTCondor Submission

`.sub` files are minimal — `Universe = vanilla`, a fixed `request_memory`, and
`Queue 1`:

```
Universe = vanilla

Output = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).out
Error = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).err
Log = /usatlas/u/qlei/batch_output_files/truth3/native/myjob.$(Cluster).$(Process).log

Executable = /usatlas/u/qlei/AF-Benchmarking/TRUTH3/BNL/Native/run_truth3_native_batch.sh

request_memory = 3G

Queue 1
```

## Schedule

`CrontabFiles/crontab_bnl.txt` installs all 11 jobs on the same cadence —
`0 */6 * * *`, i.e. every 6 hours on the hour:

```
# Rucio Script
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/Rucio/cron_rucio_bnl.sh

# EVNT Scripts
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/EVNT/BNL/CentOS7/centos_cron.sh
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/EVNT/BNL/EL9/el_cron.sh
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/EVNT/BNL/Native/native_cron.sh

# TRUTH3 Scripts
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/TRUTH3/BNL/CentOS7/cron_centos_batch.sh
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/TRUTH3/BNL/EL9/cron_el_batch.sh
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/TRUTH3/BNL/Native/cron_native_batch.sh

# Coffea Metrics
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/coffea/BNL/cron_example.sh

# FastFrames Script
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/fastframes/BNL/crontab_fastframes.sh

# EventLoop Arrays Script
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/columnar/cron_eventloop_arrays.sh

# EventLoop No Arrays Script
0 */6 * * * /usatlas/u/qlei/AF-Benchmarking/NTuple_Hist/event_loop/BNL/standard/cron_eventloop_noarrays.sh
```

Only the 3 TRUTH3 batch variants are scheduled here — the `_i` interactive
variants below are not on any crontab.

## TRUTH3 Interactive Variants

`TRUTH3/BNL/` has `CentOS7_i/`, `EL9_i/`, and `Native_i/` directories alongside
the batch ones. These run under a different account (`jroblesgo`, rather than
the batch pipeline's `qlei`), with no HTCondor `.sub` file at all — the cron
entry just `cd`s into a job directory and runs the executable directly on the
login node:

```bash
#! /bin/bash
job_dir="/atlasgpfs01/usatlas/data/jroblesgo/TRUTH3Job/native_i"

if [ -d ${job_dir} ]; then
  cd "${job_dir}" || exit
  /usatlas/u/jroblesgo/AF-Benchmarking/TRUTH3/BNL/Native_i/run_truth3_native_interactive.sh
fi
```

The interactive job executable itself never sources `benchmark_utils.sh` and
never calls `append_benchmark` — it runs `Derivation_tf.py`, moves the resulting
logs to an output directory, and stops there. No benchmark data from these runs
reaches Kibana.
