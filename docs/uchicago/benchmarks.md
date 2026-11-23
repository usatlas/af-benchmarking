# UChicago Benchmark Workflow

**File:** `.github/workflows/uchicago.yml`

This workflow runs automated benchmark jobs at the UChicago Analysis Facility to
measure performance across different job types and configurations.

## Trigger

The workflow runs:

- **Every 6 hours** (on schedule: `0 */6 * * *`)
- **On pull requests** to `main`
- **Manually** via `workflow_dispatch`

## Benchmark Jobs

The workflow runs 14 parallel benchmark jobs on `arc-runner-set-uchicago`
runners:

| Job                          | Script                                                                   | Log File                         | Description                                 |
| ---------------------------- | ------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------- |
| `rucio`                      | `./Rucio/rucio_script.sh`                                                | `rucio.log`                      | Download data using Rucio                   |
| `evnt-native`                | `./EVNT/UC/Native/run_evnt_native_batch.sh`                              | `log.generate`                   | EVNT generation (native)                    |
| `evnt-el9`                   | `./EVNT/UC/EL9/run_evnt_el9_batch.sh`                                    | `log.generate`                   | EVNT generation (EL9 container)             |
| `evnt-centos7`               | `./EVNT/UC/CentOS7/run_evnt_centos7_batch.sh`                            | `log.generate`                   | EVNT generation (CentOS7 container)         |
| `truth3-native`              | `./TRUTH3/UC/Native/run_truth3_native_batch.sh`                          | `log.Derivation`                 | TRUTH3 derivation (native)                  |
| `truth3-el9`                 | `./TRUTH3/UC/EL9/run_truth3_el9_batch.sh`                                | `log.Derivation`                 | TRUTH3 derivation (EL9 container)           |
| `truth3-centos7`             | `./TRUTH3/UC/CentOS7/run_truth3_centos7_batch.sh`                        | `log.EVNTtoDAOD`                 | TRUTH3 derivation (CentOS7 container)       |
| `coffea`                     | `./NTuple_Hist/coffea/UC/run_example.sh`                                 | `coffea_hist.log`                | NTuple to histogram (Coffea)                |
| `coffea-rntuple`             | `./NTuple_Hist/coffea/UC/run_example.sh rntuple`                         | `coffea_hist_rntuple.log`        | NTuple to histogram (Coffea, RNTuple input) |
| `eventloop-columnar`         | `./NTuple_Hist/event_loop/UC/columnar/run_eventloop_arrays.sh`           | `eventloop_arrays.log`           | Event loop (columnar)                       |
| `eventloop-columnar-rntuple` | `./NTuple_Hist/event_loop/UC/columnar/run_eventloop_arrays.sh rntuple`   | `eventloop_arrays_rntuple.log`   | Event loop (columnar, RNTuple input)        |
| `eventloop-standard`         | `./NTuple_Hist/event_loop/UC/standard/run_eventloop_noarrays.sh`         | `eventloop_noarrays.log`         | Event loop (standard)                       |
| `eventloop-standard-rntuple` | `./NTuple_Hist/event_loop/UC/standard/run_eventloop_noarrays.sh rntuple` | `eventloop_noarrays_rntuple.log` | Event loop (standard, RNTuple input)        |
| `fastframes`                 | `./NTuple_Hist/fastframes/UC/run_fastframes.sh`                          | `fastframes.log`                 | NTuple to histogram (FastFrames)            |
| `fastframes-rntuple`         | `./NTuple_Hist/fastframes/UC/run_fastframes.sh rntuple`                  | `fastframes_rntuple.log`         | NTuple to histogram (FastFrames, RNTuple)   |

## Workflow Steps

Each job follows this pattern:

1. **Checkout** - Clone the repository
2. **Setup Globus** (if required) - Configure VOMS certificates for data access
3. **Execute** - Run the benchmark script
4. **Parse** - Parse logs and generate JSON payload (via
   [parse action](../workflows/parsing.md))
5. **Upload to Kibana** - Send results to LogStash/Kibana (via
   [upload action](../workflows/parsing.md))
6. **Upload Logs** - Store log files as GitHub artifacts

### Example Job Structure

{% raw %}

```yaml
rucio:
  runs-on: arc-runner-set-uchicago
  steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

    - uses: ./.github/actions/setup-globus
      with:
        voms-usercert: ${{ secrets.VOMS_USERCERT }}
        voms-userkey: ${{ secrets.VOMS_USERKEY }}

    - name: execute
      run: ./Rucio/rucio_script.sh uchicago
      shell: bash
      env:
        VOMS_PASSWORD: ${{ secrets.VOMS_PASSWORD }}

    - name: parse benchmark log
      if: always()
      uses: ./.github/actions/parse
      with:
        job: rucio
        log-file: rucio.log
        log-type: rucio
        cluster: UC-AF
        kibana-token: ${{ secrets.KIBANA_TOKEN || 'default-token' }}
        kibana-kind: "benchmark"
        host: ${{ env.NODE_NAME }}
        os: alma9
        mode: batch
        containerized: "false"

    - name: upload to kibana
      if: always()
      uses: ./.github/actions/upload
      with:
        payload-file: payload.json
        kibana-uri: ${{ secrets.KIBANA_URI }}

    - name: upload log
      if: always()
      uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
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
2. Select the "uchicago" workflow
3. Click on a specific run to see job details

### Checking Logs

- **Benchmark logs:** Download from workflow artifacts (available for 90 days)
- **Workflow logs:** View in the GitHub Actions UI
- **Parsing errors:** Check the "parse benchmark log" step logs
- **Upload errors:** Check the "upload to kibana" step logs

### Common Issues

**Benchmark job failures:**

- Check VOMS credentials are valid
- Verify runner has network access to required resources
- Review benchmark script logs in artifacts

**Parsing failures:**

- Check that log files are generated correctly
- Verify parsing script output in "parse benchmark log" step logs
- Check token and kind values are correct

**Upload failures:**

- Verify payload.json was generated by parse step
- Check HTTP response status in "upload to kibana" step logs
- Verify kibana-uri is correct

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
each have an `-rntuple` twin. The twin runs the same analysis on the RNTuple
copy of the same dataset (see
[TTree to RNTuple Conversion](../workflows/rntuple-conversion.md)), so the two
formats can be compared run for run. Each script takes the format as its first
argument (`ttree` by default), and the RNTuple jobs write `*_rntuple.log`.

- **Coffea** runs the RNTuple twin in virtual-array mode (`processor.Runner`)
  rather than the dask-awkward mode of the TTree job. Dask mode crashes on
  RNTuple input: coffea asks every field for a `title`, which uproot's RNTuple
  fields do not have, and chunks that start mid-cluster come back as jagged
  arrays whose offsets the dask path does not expect. Patching both is still not
  enough. Virtual-array mode reads RNTuple unpatched and fills the same
  histogram as the TTree job. It reads the RNTuple dataset file list
  (`af_v2_700402_rntuple.json`) in chunks of about 51,134 entries, the list's
  largest per-file step; coffea splits each file evenly near that size, so the
  chunks are close to, but not exactly, the dask job's. Its reported time covers
  the whole run, including opening the files, whereas the dask job times only
  the computation of its prebuilt graph.
- **EventLoop (columnar)** binds each field's pointer in the `RNTupleReader`'s
  entry once and calls `LoadEntry` for every event. This is the RNTuple
  counterpart of `SetBranchAddress`.
- **EventLoop (standard)** looks each field up by name on every event. This is
  the counterpart of reading `event.branch` while iterating a TTree.
- **FastFrames** reads RNTuple from version 7.0, so both FastFrames jobs run
  FastFrames 7.2.0 built against `StatAnalysis,0.7.3`. The build is the one in
  the workflow's `FF_DIR` (`/data/qlei/fastframes_v7` at UC);
  `NTuple_Hist/fastframes/UC-ODF/build_fastframes.sh` builds one. The RNTuple
  config differs from the TTree one only in its file list
  (`mc20e_filelist_rntuple.txt`). The earlier 6.1.0 build (`StatAnalysis,0.6.3`)
  read only TTrees, so the TTree job's history changes version at the switch.

UC-ODF runs the same RNTuple jobs; where its RNTuple copy and FastFrames 7.2
build live, and how to rebuild the build, is on the
[UC-ODF page](../uc-odf/benchmarks.md#data-on-the-runner).

The two formats' inputs are compressed differently, so a size or I/O comparison
is not a pure format comparison. See the caveat on the
[conversion page](../workflows/rntuple-conversion.md#what-to-expect).
