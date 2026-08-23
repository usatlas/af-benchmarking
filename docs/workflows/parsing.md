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

| Input          | Description                               | Required | Example                                      |
| -------------- | ----------------------------------------- | -------- | -------------------------------------------- |
| `job`          | Job name                                  | Yes      | `rucio`, `eventloop-columnar`, `evnt-native` |
| `log-file`     | Path to log file                          | Yes      | `rucio.log`                                  |
| `log-type`     | Type of log parser to use                 | Yes      | `rucio`, `athena`, `coffea`, `fastframes`    |
| `cluster`      | Cluster name                              | Yes      | `UC-AF`, `SLAC-AF`, `BNL-AF`                 |
| `kibana-token` | Token for benchmark ID                    | Yes      | From secrets                                 |
| `kibana-kind`  | Kind for benchmark ID                     | Yes      | From secrets                                 |
| `host`         | Hostname to identify the machine          | Yes      | `${NODE_NAME}`                               |
| `payload-file` | Path to payload file for size calculation | No       | Empty string (default, payloadSize = -1)     |
| `output-file`  | Output JSON file path                     | No       | `payload.json` (default)                     |

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
pixi run -e kibana python parsing/scripts/ci_parse.py \
  --job <job> \
  --log-file <log-file> \
  --log-type <log-type> \
  --cluster <cluster> \
  --token <token> \
  --kind <kind> \
  --host <host> \
  --output payload.json
```

3. **Output**: Generates `payload.json` file in the workspace

### Upload Action

The upload action performs these steps:

1. **Validate payload file**: Checks that the payload file exists and displays
   its contents for debugging
2. **Upload to LogStash**: POSTs the JSON payload using curl:

```bash
curl -X POST "https://<kibana-uri>" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -w "%{http_code}" \
  -s -o /tmp/response.txt
```

3. **Verify response**: Checks HTTP status code and fails if not 2xx

## Data Structure

The parsed data sent to LogStash (which routes it to Kibana) is validated
against a JSON schema (`parsing/schema/payload.schema.json`) to ensure
correctness before upload.

Required structure:

```json
{
  "job": "rucio",
  "cluster": "UC-AF",
  "submitTime": 1234567890000,
  "queueTime": 0,
  "runTime": 3600,
  "payloadSize": 1073741824,
  "status": 0,
  "host": "hostname.example.com",
  "token": "<TOKEN>",
  "kind": "benchmark"
}
```

### Field Descriptions

| Field         | Type    | Description                                       | Source                                                                                                    |
| ------------- | ------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `job`         | String  | Job name (e.g., `rucio`, `eventloop-columnar`)    | Passed from workflow via {% raw %} `${{ github.job }}` {% endraw %}                                       |
| `cluster`     | String  | AF cluster name (UC-AF, SLAC-AF, BNL-AF)          | Passed from workflow                                                                                      |
| `submitTime`  | Integer | UTC timestamp (ms since epoch)                    | Parsed from log                                                                                           |
| `queueTime`   | Integer | Queue time (seconds)                              | Parsed from log                                                                                           |
| `runTime`     | Integer | Execution time (seconds)                          | Parsed from log                                                                                           |
| `payloadSize` | Integer | Output file size (bytes)                          | Calculated from `payload-file` input using `Path().stat().st_size` (-1 if not provided, 0 for empty file) |
| `status`      | Integer | Exit code (0=success, non-zero=failure)           | Parsed from log                                                                                           |
| `host`        | String  | Hostname where job executed (idn-hostname format) | Passed from workflow via `${NODE_NAME}`                                                                   |
| `token`       | String  | Benchmark identifier AND LogStash routing key     | Passed from workflow (secrets)                                                                            |
| `kind`        | String  | Benchmark type AND LogStash routing kind          | Passed from workflow (secrets)                                                                            |

### Static vs Parsed Fields

**Static fields** (from workflow configuration):

- `cluster` - Set per site (UC-AF, SLAC-AF, etc.)
- `token` - Benchmark identifier token AND LogStash routing key
- `kind` - Benchmark kind/category AND LogStash routing kind
- `host` - Hostname from workflow environment (`${NODE_NAME}`)

**Parsed fields** (extracted from logs):

- `testType` - Determined from job type or log content
- `submitTime` - Start timestamp from log
- `queueTime` - Time waiting before execution
- `runTime` - Total execution duration
- `payloadSize` - Size of output files
- `status` - Job exit code

**Note:** The `token` and `kind` fields are included in the JSON document body
sent to LogStash, where they serve the dual purpose of identifying the benchmark
and routing the data to the appropriate Kibana instance.

## Failure Handling

The action uses `continue-on-error: true` in workflows, which means:

- **Parsing failures don't fail the benchmark job**
- Logs are always uploaded as artifacts
- Parsing errors are visible in workflow logs
- Benchmarks complete successfully even if Kibana upload fails

This design ensures benchmark execution is never blocked by parsing/upload
issues.

## Usage Example

{% raw %}

```yaml
- name: parse benchmark log
  if: always() # Run even if benchmark failed
  uses: ./.github/actions/parse
  with:
    job: ${{ github.job }}
    log-file: rucio.log
    log-type: rucio
    cluster: UC-AF
    kibana-token: ${{ secrets.KIBANA_TOKEN }}
    kibana-kind: ${{ secrets.KIBANA_KIND }}
    host: ${NODE_NAME}
  continue-on-error: true # Don't fail job if parsing fails

- name: upload to kibana
  if: always() # Run even if parsing failed
  uses: ./.github/actions/upload
  with:
    payload-file: payload.json
    kibana-uri: ${{ secrets.KIBANA_URI }}
  continue-on-error: true # Don't fail job if upload fails
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
3. Expand the "parse and upload to kibana" step
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

python parsing/scripts/ci_parse.py \
  --job rucio \
  --log-file path/to/rucio.log \
  --log-type rucio \
  --cluster UC-AF \
  --token $KIBANA_TOKEN \
  --kind $KIBANA_KIND \
  --host $HOSTNAME \
  --output payload.json
```

**Test upload:**

```bash
curl -X POST "https://$KIBANA_URI" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -w "\nHTTP Status: %{http_code}\n"
```

## Integration with Other Workflows

These actions are currently used by:

- [UChicago Benchmark Workflow](benchmarks.md) - All 10 benchmark jobs

Can be extended to:

- SLAC benchmark workflows
- BNL benchmark workflows
- NERSC benchmark workflows
