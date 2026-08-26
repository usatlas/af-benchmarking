# Parse and Upload Actions

**Files:**

- `.github/actions/parse/action.yml` - Parse benchmark logs
- `.github/actions/upload/action.yml` - Upload to LogStash/Kibana

These custom composite actions handle parsing benchmark logs and uploading
results to Elasticsearch/Kibana for visualization and analysis.

## Purpose

After each benchmark job completes, these actions:

1. **Parse action**: Parses the log file to extract timing and performance
   metrics, generating a JSON payload
2. **Upload action**: Sends the JSON payload to LogStash for routing and storage
   in Elasticsearch/Kibana

## Architecture

The parsing and upload workflow uses **two separate actions** to process and
send benchmark data:

```
Parse Action → payload.json → Upload Action → LogStash → Elasticsearch/Kibana
```

**Key architectural details:**

- **LogStash endpoint:** LogStash routes requests to the appropriate Kibana
  instance based on the `token` + `kind` combination
- **Authentication/Routing:** The `token` and `kind` fields are sent as part of
  the JSON document body (NOT as Bearer authentication in HTTP headers)
- **No traditional credentials:** This design eliminates the need for
  username/password authentication - routing is handled via the token+kind
  fields in the data payload

This routing approach allows different benchmark types and projects to be
automatically directed to their respective Kibana instances while maintaining a
single, simple integration point for GitHub Actions workflows.

## Inputs

### Parse Action Inputs

| Input           | Description                               | Required | Example                                                                                                                                                |
| --------------- | ----------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `job`           | Job name                                  | Yes      | `rucio`, `evnt`, `truth3`, `coffea`, `eventloop-columnar`, `eventloop-standard`, `fastframes`                                                          |
| `log-file`      | Path to log file                          | Yes      | `rucio.log`, `log.generate`, `log.Derivation`, `log.EVNTtoDAOD`, `coffea_hist.log`, `eventloop_arrays.log`, `eventloop_noarrays.log`, `fastframes.log` |
| `log-type`      | Type of log parser to use                 | Yes      | `rucio`, `evnt`, `truth3`, `coffea`, `eventloop`, `fastframes`                                                                                         |
| `cluster`       | Cluster name                              | Yes      | `UC-AF`, `SLAC-AF`, `BNL-AF`                                                                                                                           |
| `kibana-token`  | Token for benchmark ID                    | Yes      | From secrets                                                                                                                                           |
| `kibana-kind`   | Kind for benchmark ID                     | Yes      | `"benchmark"` (literal value)                                                                                                                          |
| `host`          | Hostname to identify the machine          | Yes      | `${NODE_NAME}`                                                                                                                                         |
| `payload-file`  | Path to payload file for size calculation | No       | Empty string (default, payloadSize = -1)                                                                                                               |
| `os`            | Operating system the job ran on           | Yes      | `alma9`, `centos7`                                                                                                                                     |
| `mode`          | Job execution mode                        | Yes      | `batch`, `interactive`                                                                                                                                 |
| `containerized` | Whether the job ran inside a container    | Yes      | `"true"`, `"false"`                                                                                                                                    |
| `output-file`   | Output JSON file path                     | No       | `payload.json` (default)                                                                                                                               |

### Upload Action Inputs

| Input          | Description               | Required | Example        |
| -------------- | ------------------------- | -------- | -------------- |
| `payload-file` | Path to JSON payload file | Yes      | `payload.json` |
| `kibana-uri`   | URI endpoint for LogStash | Yes      | From secrets   |

## Implementation Steps

### Parse Action

The parse action performs these steps:

1. **Setup pixi**: Sets up the `kibana` pixi environment with Python 3.13 and
   required dependencies
2. **Parse log file**: Runs the parsing script to generate JSON payload:

```bash
pixi run -e kibana python -m parsing.scripts.ci_parse \
  --job <job> \
  --log-file <log-file> \
  --log-type <log-type> \
  --cluster <cluster> \
  --token <token> \
  --kind <kind> \
  --host <host> \
  --os <os> \
  --mode <mode> \
  --containerized <containerized> \
  --output payload.json
```

3. **Output**: Generates `payload.json` file in the workspace

### Upload Action

The upload action performs these steps:

1. **Validate payload file**: Checks that the payload file exists and displays
   its contents for debugging
2. **Upload to LogStash**: POSTs the JSON payload using curl:

```bash
curl -X POST "<kibana-uri>" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -w "%{http_code}" \
  -s -o response.txt
```

3. **Verify response**: Checks HTTP status code and fails if not 2xx

## Data Structure

The parsed data sent to LogStash (which routes it to Kibana) is validated
against a JSON schema (`parsing/schema/payload.schema.json`) to ensure
correctness before upload.

Required structure:

```json
{
  "submitTime": 1787510063000,
  "queueTime": 0,
  "runTime": 337,
  "status": 0,
  "setupTime": 4,
  "cpuPercent": 95.0,
  "maxRssKb": 1600792,
  "job": "evnt",
  "cluster": "UC-AF",
  "payloadSize": -1,
  "token": "***",
  "kind": "benchmark",
  "host": "g006.af.uchicago.edu",
  "os": "alma9",
  "mode": "batch",
  "containerized": false
}
```

### Field Descriptions

| Field           | Type    | Description                                       | Source                                                                                                    |
| --------------- | ------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `job`           | String  | Job name (e.g., `rucio`, `evnt`, `truth3`)        | Passed from workflow as a literal value                                                                   |
| `cluster`       | String  | AF cluster name (UC-AF, SLAC-AF, BNL-AF)          | Passed from workflow                                                                                      |
| `submitTime`    | Integer | UTC timestamp (ms since epoch)                    | Parsed from log                                                                                           |
| `queueTime`     | Integer | Queue time (seconds)                              | Parsed from log                                                                                           |
| `runTime`       | Integer | Execution time (seconds)                          | Parsed from log                                                                                           |
| `payloadSize`   | Integer | Output file size (bytes)                          | Calculated from `payload-file` input using `Path().stat().st_size` (-1 if not provided, 0 for empty file) |
| `status`        | Integer | Exit code (0=success, non-zero=failure)           | Parsed from log                                                                                           |
| `host`          | String  | Hostname where job executed (idn-hostname format) | Passed from workflow via the `NODE_NAME` environment variable                                             |
| `setupTime`     | Integer | Environment setup time (seconds), optional        | Parsed from log, when present                                                                             |
| `cpuPercent`    | Number  | CPU usage percentage, optional                    | Parsed from `/usr/bin/time -v` output, when present                                                       |
| `maxRssKb`      | Integer | Maximum resident set size (KB), optional          | Parsed from `/usr/bin/time -v` output, when present                                                       |
| `os`            | String  | Operating system (`centos7`, `alma9`)             | Passed from workflow as a literal value                                                                   |
| `mode`          | String  | Job execution mode (`batch`, `interactive`)       | Passed from workflow as a literal value                                                                   |
| `containerized` | Boolean | Whether the job ran inside a container            | Passed from workflow as a literal value                                                                   |
| `token`         | String  | Benchmark identifier AND LogStash routing key     | Passed from workflow (secrets, with a hardcoded fallback)                                                 |
| `kind`          | String  | Benchmark type AND LogStash routing kind          | Passed from workflow as a literal value                                                                   |

### Static vs Parsed Fields

**Static fields** (from workflow configuration):

- `job` - Job name, a literal value per job
- `cluster` - Set per site (UC-AF, SLAC-AF, etc.)
- `token` - Benchmark identifier token AND LogStash routing key
- `kind` - Benchmark kind/category AND LogStash routing kind
- `host` - Hostname from the `NODE_NAME` environment variable
- `os` - Operating system, a literal value per job
- `mode` - Execution mode, a literal value per job
- `containerized` - Whether the job runs in a container, a literal value per job

**Parsed fields** (extracted from logs):

- `submitTime` - Start timestamp from log
- `queueTime` - Time waiting before execution
- `runTime` - Total execution duration
- `payloadSize` - Size of output files
- `status` - Job exit code
- `setupTime` - Environment setup time, when present in the log
- `cpuPercent` - CPU usage percentage, when present in the log
- `maxRssKb` - Maximum resident set size, when present in the log

**Note:** The `token` and `kind` fields are included in the JSON document body
sent to LogStash, where they serve the dual purpose of identifying the benchmark
and routing the data to the appropriate Kibana instance.

## Failure Handling

Neither action uses `continue-on-error`, so a parsing or upload failure fails
the benchmark job:

- **A parsing failure fails the job** — the `parse benchmark log` step's
  `if: always()` only guarantees it _runs_ even if the benchmark script failed,
  not that its own failure is tolerated
- **An upload failure fails the job** the same way
- Logs are still uploaded as artifacts regardless, since the "upload log" step
  also uses `if: always()`
- Parsing and upload errors are visible in the workflow's job logs

## Usage Example

{% raw %}

```yaml
- name: parse benchmark log
  if: always() # Run even if benchmark failed
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
  if: always() # Run even if parsing failed
  uses: ./.github/actions/upload
  with:
    payload-file: payload.json
    kibana-uri: ${{ secrets.KIBANA_URI }}
```

{% endraw %}

## LogStash/Elasticsearch Configuration

Data is sent to LogStash, which routes it to Elasticsearch:

- **LogStash endpoint:** this acts as routing service
- **Elasticsearch index:** `af_benchmarks`
- **Protocol:** HTTPS
- **Routing/Authentication:** Via `token` + `kind` fields in the JSON document
  body

The `token` and `kind` fields serve a dual purpose:

1. **Benchmark identification:** Uniquely identify and categorize the benchmark
   run
2. **LogStash routing:** Direct the data to the appropriate Kibana instance

This body-based routing mechanism eliminates the need for traditional HTTP
authentication headers or stored credentials.

## Debugging

### Viewing Parsing Logs

1. Go to the workflow run in GitHub Actions
2. Click on the specific job
3. Expand the "parse benchmark log" or "upload to kibana" step
4. Review the output for parsing errors

### Common Parsing Issues

**Log file not found:**

- Verify the log file path matches the actual output
- Check that the benchmark script completed
- Look for the file in workflow artifacts

**Parsing errors:**

- Check log file format matches expected structure
- Verify parsing script handles this job type
- Review error messages in workflow logs

**Upload failures:**

- Check network connectivity to LogStash endpoint
- Verify `token` and `kind` values are correctly set
- Ensure the `af_benchmarks` index exists in Elasticsearch

### Testing Locally

Test parsing and upload separately:

**Test parsing:**

```bash
pixi shell -e kibana

python -m parsing.scripts.ci_parse \
  --job rucio \
  --log-file path/to/rucio.log \
  --log-type rucio \
  --cluster UC-AF \
  --token $KIBANA_TOKEN \
  --kind $KIBANA_KIND \
  --host $HOSTNAME \
  --os alma9 \
  --mode batch \
  --containerized false \
  --output payload.json
```

**Test upload:**

```bash
curl -X POST "$KIBANA_URI" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -w "\nHTTP Status: %{http_code}\n"
```

## Integration with Other Workflows

These actions are currently used by:

- [UChicago Benchmark Workflow](../uchicago/benchmarks.md) - All 11 benchmark
  jobs

Can be extended to:

- SLAC benchmark workflows
- BNL benchmark workflows
- NERSC benchmark workflows
