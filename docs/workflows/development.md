# Development Guide

This guide covers local development, testing, and adding new benchmark
workflows.

## Local Development Setup

### Prerequisites

Install [pixi](https://pixi.sh):

```bash
# macOS
brew install pixi

# Linux/Windows
curl -fsSL https://pixi.sh/install.sh | bash
```

### Clone Repository

```bash
git clone https://github.com/usatlas/af-benchmarking.git
cd af-benchmarking
```

## Testing Workflows Locally

### Testing Documentation

```bash
# Build documentation
pixi run -e docs build

# Serve with live reload
pixi run -e docs serve

# Build and validate all links
pixi run -e docs build-check

# Validate links only (requires build-no-dir-urls first)
pixi run -e docs validate
```

Open http://127.0.0.1:8000 to preview documentation.

### Testing Parsing

```bash
# Enter the kibana environment
pixi shell -e kibana

# Run parsing script to generate payload.json
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

# Test upload to LogStash
curl -X POST "$KIBANA_URI" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -w "\nHTTP Status: %{http_code}\n"
```

### Testing Benchmark Scripts

Run benchmark scripts directly on the appropriate system:

```bash
# On UChicago AF
./Rucio/rucio_script.sh uchicago
./EVNT/UC/Native/run_evnt_native_batch.sh
./TRUTH3/UC/Native/run_truth3_native_batch.sh
./NTuple_Hist/coffea/UC/run_example.sh
# etc.
```

## Adding New Benchmarks

To add a new benchmark job to the UChicago workflow:

### 1. Create Benchmark Script

Create your benchmark script in the appropriate directory:

```bash
mkdir -p NewBenchmark/UC
touch NewBenchmark/UC/run_new_benchmark.sh
chmod +x NewBenchmark/UC/run_new_benchmark.sh
```

Ensure the script:

- Generates a log file in a predictable location
- Includes timing information
- Outputs payload size information
- Returns appropriate exit codes

### 2. Add Job to Workflow

Edit `.github/workflows/uchicago.yml` and add a new job:

{% raw %}

```yaml
new-benchmark:
  runs-on: arc-runner-set-uchicago
  steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

    # Add setup steps if needed (e.g., Globus)
    - uses: ./.github/actions/setup-globus
      with:
        voms-usercert: ${{ secrets.VOMS_USERCERT }}
        voms-userkey: ${{ secrets.VOMS_USERKEY }}

    - name: execute
      run: ./NewBenchmark/UC/run_new_benchmark.sh
      shell: bash
      env:
        VOMS_PASSWORD: ${{ secrets.VOMS_PASSWORD }}

    - name: parse benchmark log
      if: always()
      uses: ./.github/actions/parse
      with:
        job: new-benchmark # Update to match your job name
        log-file: new-benchmark.log # Update to match your log file
        log-type: new-benchmark # Update to match your parser type
        cluster: UC-AF
        kibana-token: ${{ secrets.KIBANA_TOKEN || 'default-token' }}
        kibana-kind: "benchmark"
        host: ${{ env.NODE_NAME }}
        os: alma9 # Update to match the OS the job runs on
        mode: batch # Or "interactive"
        containerized: "false" # Or "true"

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
          new-benchmark.log # Update to match your log file
```

{% endraw %}

### 3. Update Parsing Scripts

Coordinate with Juan to update parsing scripts to handle the new log format:

- Define log parsing logic for the new benchmark
- Extract timing metrics (submitTime, queueTime, runTime)
- Extract payload size
- Determine exit status
- Decide the `os`, `mode`, and `containerized` values for the new job

### 4. Test Locally

Before committing:

1. **Run the benchmark script** manually on UC AF
2. **Verify log file** is generated correctly
3. **Test parsing** with a sample log file
4. **Check workflow syntax** with yamllint or GitHub's workflow editor

### 5. Create Pull Request

1. **Create feature branch:**

```bash
git checkout -b feat/add-new-benchmark
```

2. **Commit changes:**

```bash
git add .github/workflows/uchicago.yml NewBenchmark/
git commit -m "feat: add new benchmark workflow"
```

3. **Push and create PR:**

```bash
git push -u origin feat/add-new-benchmark
```

4. **Open pull request** on GitHub

### 6. Monitor First Run

After merging:

1. Watch the workflow run in GitHub Actions
2. Check that the job completes successfully
3. Verify logs are uploaded as artifacts
4. Confirm data appears in Kibana
5. Review parsing logs for any errors

## Monitoring and Debugging

### Viewing Workflow Runs

1. Go to [Actions tab](https://github.com/usatlas/af-benchmarking/actions)
2. Select the workflow (e.g., "uchicago")
3. Click on a specific run
4. Review job details and logs

### Downloading Logs

```bash
# Using gh CLI
gh run download <run-id>

# Or download from web UI
# Actions → Workflow Run → Artifacts
```

### Debugging Workflow Issues

**Workflow won't trigger:**

- Check workflow file syntax (YAML errors)
- Verify trigger conditions (schedule, PR, etc.)
- Ensure workflow is enabled in repository settings

**Job failures:**

- Review job logs in GitHub Actions UI
- Check for authentication issues (secrets)
- Verify runner has necessary access
- Look for script errors in execute step

**Parsing failures:**

- Check "parse benchmark log" step logs
- Verify log file exists and has expected format
- Test parsing script locally
- Check token and kind values are correct

**Upload failures:**

- Check "upload to kibana" step logs
- Verify payload.json was generated by parse step
- Check HTTP response status and body in logs
- Verify kibana-uri is correct

**Artifact upload failures:**

- Verify artifact path is correct
- Check file exists before upload step
- Review artifact size limits (too large?)

### Common Issues

**VOMS authentication:**

```bash
# Verify secrets are set:
# - VOMS_USERCERT
# - VOMS_USERKEY
# - VOMS_PASSWORD
```

**Runner access:**

- Ensure runner can access data sources
- Check network/firewall rules
- Verify mount points exist

**Log file location:**

- Double-check log file path matches actual output
- Use absolute paths if needed
- Check working directory

## Pre-commit Hooks

This project uses pre-commit for linting and formatting:

```bash
# Install pre-commit
pip install pre-commit  # or: brew install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Pixi Tasks

List available tasks:

```bash
# List all tasks
pixi task list

# List docs environment tasks
pixi task list -e docs

# List kibana environment tasks
pixi task list -e kibana
```

Run tasks:

```bash
# Documentation tasks
pixi run -e docs build
pixi run -e docs serve
pixi run -e docs build-check
pixi run -e docs validate

# Custom kibana tasks (if defined)
pixi run -e kibana <task-name>
```

## Environment Variables

For local testing, set these environment variables:

```bash
# Kibana/LogStash configuration
export KIBANA_TOKEN="your-kibana-token"
export KIBANA_KIND="your-kibana-kind"
export KIBANA_URI="your-kibana-uri"

# VOMS credentials (if testing with Globus)
export VOMS_PASSWORD="your-voms-password"
```

Never commit these values to git!

## Contributing Workflow

See
[CONTRIBUTING.md](https://github.com/usatlas/af-benchmarking/blob/main/.github/CONTRIBUTING.md)
for the full contribution guidelines.

1. **Create feature branch** from `main`
2. **Make changes** (code, docs, workflows)
3. **Test locally** using pixi
4. **Run pre-commit** checks
5. **Commit** with conventional commit message
6. **Push** and create pull request
7. **Address review** comments
8. **Merge** after approval

### Conventional Commits

Use semantic commit messages:

```bash
feat: add new rucio benchmark
fix: correct parsing for truth3 logs
docs: update workflow documentation
chore: update dependencies
```
