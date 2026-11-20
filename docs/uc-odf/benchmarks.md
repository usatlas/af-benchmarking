# UC-ODF Benchmark Workflow

**File:** `.github/workflows/uc-odf.yml`

This workflow runs automated benchmark jobs at the UC-ODF analysis facility to
measure performance across different job types and configurations. It is the
counterpart of the [UChicago workflow](../uchicago/benchmarks.md): the same
fifteen jobs and the same parsing and upload. The steps match too, except that
the FastFrames jobs here need no Globus setup.

## The Open Data Facility

ODF stands for **Open Data Facility**. It is a JupyterHub-based analysis
facility that runs on Kubernetes: users get notebooks and terminals with CVMFS
mounted and their own persistent `/data` volume, and there is no batch system
(no HTCondor or Slurm). That is why the benchmarks run as a GitHub Actions
workflow, as they do at UChicago.

The jobs run on ephemeral runners from the `arc-runner-set-odf` runner scale
set. Each runner:

- is a container with an **AlmaLinux 9** image, so the native jobs run directly
  on it exactly as they do at UChicago, while the container-variant jobs start
  `setupATLAS -c el9` or `-c centos7` containers from inside the runner
- has **CVMFS** mounted at `/cvmfs`, and an 8 GiB in-memory `/dev/shm` that
  Athena's shared writer needs
- shares the cluster's nodes with JupyterHub users, and at most **8 runners**
  run at the same time, so the 15 jobs do not all run at once

### Data on the runner

A persistent volume is mounted on every runner at `/data/af-benchmarking` and
survives between runs. The workflow sets two locations once, for all jobs:

| Variable     | Path                                                                             | Used by                                   |
| ------------ | -------------------------------------------------------------------------------- | ----------------------------------------- |
| `NTUPLE_DIR` | `/data/af-benchmarking/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root` | the coffea, EventLoop and FastFrames jobs |
| `FF_DIR`     | `/data/af-benchmarking/FastFramesTutorial`                                       | `fastframes`, `fastframes-rntuple`        |

`NTUPLE_DIR` holds the 18 mc20e ntuples (about 20 GB), staged by an
administrator. The `-rntuple` jobs read the RNTuple copy next to it instead:
each script strips a trailing `/`, then puts `_RNTuple` before `.root`
(`..._ANALYSIS_RNTuple.root`). That copy has to be staged too, with the same 18
file names; see
[TTree to RNTuple Conversion](../uchicago/rntuple-conversion.md).

`FF_DIR` holds a FastFrames 7.2.0 build made under `StatAnalysis,0.7.3`, the
release `run_fastframes.sh` sets up. To rebuild it, check out FastFrames v7.2.0
in `FF_DIR/FastFrames` and run, as a user who can write to `FF_DIR`:

```bash
FF_DIR=/data/af-benchmarking/FastFramesTutorial JOBS=4 \
  ./NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh
```

The script removes any earlier build trees first. `JOBS` sets the compile
parallelism (default 1). The jobs only read both locations, and nothing in the
workflow writes to the volume.

## Trigger

The workflow runs:

- **Every 6 hours** (on schedule: `0 */6 * * *`)
- **On pull requests** to `main`
- **Manually** via `workflow_dispatch`

Pull request runs skip the upload to Kibana, so test runs do not reach the
dashboards. Scheduled and manual runs upload. Pull requests from forks and from
dependabot run no jobs, and a new push to a pull request cancels the run still
in progress for it.

## Benchmark Jobs

The workflow runs 15 parallel benchmark jobs on `arc-runner-set-odf` runners (at
most 8 at a time). The NTuple scripts take the input format as their first
argument, `ttree` (the default) or `rntuple`:

| Job                          | Script                                                                       | Log File                         | Description                           |
| ---------------------------- | ---------------------------------------------------------------------------- | -------------------------------- | ------------------------------------- |
| `rucio`                      | `./Rucio/rucio_script.sh odf`                                                | `rucio.log`                      | Download data using Rucio             |
| `evnt-native`                | `./EVNT/UC-ODF/Native_i/run_evnt_native_interactive.sh`                      | `log.generate`                   | EVNT generation (native)              |
| `evnt-el9`                   | `./EVNT/UC-ODF/EL9_i/run_evnt_el9_interactive.sh`                            | `log.generate`                   | EVNT generation (EL9 container)       |
| `evnt-centos7`               | `./EVNT/UC-ODF/CentOS7_i/run_evnt_centos7_interactive.sh`                    | `log.generate`                   | EVNT generation (CentOS7 container)   |
| `truth3-native`              | `./TRUTH3/UC-ODF/Native_i/run_truth3_native_interactive.sh`                  | `log.Derivation`                 | TRUTH3 derivation (native)            |
| `truth3-el9`                 | `./TRUTH3/UC-ODF/EL9_i/run_truth3_el9_interactive.sh`                        | `log.Derivation`                 | TRUTH3 derivation (EL9 container)     |
| `truth3-centos7`             | `./TRUTH3/UC-ODF/CentOS7_i/run_truth3_centos7_interactive.sh`                | `log.EVNTtoDAOD`                 | TRUTH3 derivation (CentOS7 container) |
| `coffea`                     | `./NTuple_Hist/coffea/UC-ODF/run_example.sh`                                 | `coffea_hist.log`                | NTuple to histogram (Coffea)          |
| `coffea-rntuple`             | `./NTuple_Hist/coffea/UC-ODF/run_example.sh rntuple`                         | `coffea_hist_rntuple.log`        | Coffea on RNTuple                     |
| `eventloop-columnar`         | `./NTuple_Hist/event_loop/UC-ODF/columnar/run_eventloop_arrays.sh`           | `eventloop_arrays.log`           | Event loop (columnar)                 |
| `eventloop-columnar-rntuple` | `./NTuple_Hist/event_loop/UC-ODF/columnar/run_eventloop_arrays.sh rntuple`   | `eventloop_arrays_rntuple.log`   | Event loop (columnar) on RNTuple      |
| `eventloop-standard`         | `./NTuple_Hist/event_loop/UC-ODF/standard/run_eventloop_noarrays.sh`         | `eventloop_noarrays.log`         | Event loop (standard)                 |
| `eventloop-standard-rntuple` | `./NTuple_Hist/event_loop/UC-ODF/standard/run_eventloop_noarrays.sh rntuple` | `eventloop_noarrays_rntuple.log` | Event loop (standard) on RNTuple      |
| `fastframes`                 | `./NTuple_Hist/fastframes/UC-ODF/run_fastframes.sh`                          | `fastframes.log`                 | NTuple to histogram (FastFrames)      |
| `fastframes-rntuple`         | `./NTuple_Hist/fastframes/UC-ODF/run_fastframes.sh rntuple`                  | `fastframes_rntuple.log`         | FastFrames on RNTuple                 |

How each framework reads RNTuple, including why coffea's RNTuple job runs in
virtual-array mode rather than the dask mode its TTree job uses, is described on
the [UChicago page](../uchicago/benchmarks.md). One difference here: FastFrames
uses a single config for both formats, because `run_fastframes.sh` writes the
file list (`fastframes_run/mc20e_filelist.txt`) from the format's ntuple
directory.

/// note | Native and container jobs

The `native` jobs run directly on the runner. Every other job runs inside a
`setupATLAS` container started from the runner. The `_i` in the script folder
names is only a naming convention carried over from UChicago's interactive
variants; all of these jobs run in the workflow as `batch` jobs.

///

## Workflow Steps

Each job follows this pattern:

1. **Checkout** - Clone the repository
2. **Export node name** - Record the runner's node name as the reported host
3. **Setup Globus** (Rucio only) - Configure VOMS certificates for data access,
   and write the password file the Rucio script reads
4. **Execute** - Run the benchmark script
5. **Locate log** (Rucio only) - Copy `rucio.log` out of the timestamped
   directory the Rucio script writes it to
6. **Parse** - Parse logs and generate JSON payload (via
   [parse action](../workflows/parsing.md))
7. **Upload to Kibana** - Send results to LogStash/Kibana (via
   [upload action](../workflows/parsing.md)); skipped on pull requests
8. **Upload Logs** - Store log files as GitHub artifacts

### Example Job Structure

{% raw %}

```yaml
rucio:
  runs-on: arc-runner-set-odf
  steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      with:
        persist-credentials: false

    - name: Export node name
      run: echo "NODE_NAME=$NODE_NAME" >> "$GITHUB_ENV"

    - uses: $/.github/actions/setup-globus
      with:
        voms-usercert: ${{ secrets.VOMS_USERCERT }}
        voms-userkey: ${{ secrets.VOMS_USERKEY }}

    - name: write VOMS password file
      run: |
        mkdir -p ~/af_benchmarking/rucio
        printf '%s' "$VOMS_PASSWORD" > ~/af_benchmarking/rucio/pass.txt
        chmod 600 ~/af_benchmarking/rucio/pass.txt
      shell: bash
      env:
        VOMS_PASSWORD: ${{ secrets.VOMS_PASSWORD }}

    - name: execute
      run: ./Rucio/rucio_script.sh odf
      shell: bash

    - name: locate rucio log
      if: always()
      run:
        cp "$(ls -td ~/af_benchmarking/rucio/logs/*/ | head -1)rucio.log"
        rucio.log
      shell: bash

    - name: parse benchmark log
      if: always()
      uses: $/.github/actions/parse
      with:
        job: rucio
        log-file: rucio.log
        log-type: rucio
        cluster: UC-ODF
        kibana-token: ${{ secrets.KIBANA_TOKEN || 'default-token' }}
        kibana-kind: "benchmark"
        host: ${{ env.NODE_NAME }}
        os: alma9
        mode: batch
        containerized: "true"

    - name: upload to kibana
      if: always() && github.event_name != 'pull_request'
      uses: $/.github/actions/upload
      with:
        payload-file: payload.json
        kibana-uri: ${{ secrets.KIBANA_URI }}

    - name: upload log
      if: always()
      uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
      with:
        name: ${{ github.job }}-logs
        path: |
          rucio.log
```

{% endraw %}

## Monitoring Results

### Viewing Workflow Runs

1. Go to the repository's
   [Actions tab](https://github.com/usatlas/af-benchmarking/actions)
2. Select the "uc-odf" workflow
3. Click on a specific run to see job details

### Checking Logs

- **Benchmark logs:** Download from workflow artifacts (available for 90 days)
- **Workflow logs:** View in the GitHub Actions UI
- **Parsing errors:** Check the "parse benchmark log" step logs
- **Upload errors:** Check the "upload to kibana" step logs

### Common Issues

**Benchmark job failures:**

- Check VOMS credentials are valid (Rucio)
- Check that `/data/af-benchmarking` is mounted on the runner, that `NTUPLE_DIR`
  and its `_RNTuple` copy each hold all 18 ntuples, and that the FastFrames 7.2
  build exists in `FF_DIR`
- For the container jobs, look for `setupATLAS` errors at the start of the job
  log
- Review benchmark script logs in artifacts

**Empty or missing ntuples:**

If a format's ntuple directory does not exist (for example, the volume is not
mounted), the coffea and EventLoop scripts print `no ntuple directory at ...`
and exit before any setup. No log is written, so the parse step fails. If the
directory exists but is empty, the EventLoop jobs process zero events and finish
successfully, so the run uploads a very short, successful-looking benchmark:
check `events_processed` in the log. Coffea fails on the missing files, and the
FastFrames job stops when it finds no `.root` files.

**FastFrames not built:**

If `FF_DIR` has no build, the FastFrames job fails when it sources
`TutorialClass/build/setup.sh` inside the container and never runs FastFrames.
The parse step then fails because the histogram file it measures,
`fastframes_run/example_FS.root`, does not exist. A build made under a different
StatAnalysis release fails at the same point with a cling error about a missing
resource directory.

**Parsing failures:**

- Check that log files are generated correctly
- Verify parsing script output in "parse benchmark log" step logs
- Check token and kind values are correct

**Upload failures:**

- Verify payload.json was generated by parse step
- Check HTTP response status in "upload to kibana" step logs
- Verify kibana-uri is correct

### Reading the numbers

/// note | Things to know when reading UC-ODF results

- `setupTime` is not reliable for the container jobs. It reads 1-2 seconds even
  when starting the container and installing packages takes much longer.
  `runTime` covers the whole script.
- While both sites ran FastFrames 6.1, it ran several times faster here than at
  UChicago with the same event count, and the difference was not explained. Both
  sites now run 7.2; until the two are compared again, do not compare FastFrames
  numbers across sites.
- Coffea's RNTuple job runs in virtual-array mode, so its timing includes
  opening the files and is not directly comparable with the TTree job's.
- Coffea's `maxRssKb` is the main Python process only. The memory of its dask
  workers is not included.
- Jobs share nodes with each other and with JupyterHub users, so timings can
  vary from run to run.

///

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
