# Command-Line Interface Guide

The moana-qc package provides command-line tools for use in Cylc workflows and manual processing.

## Installation

After installing the package, three CLI commands are available:

```bash
moana-qc         # Quality control processing
moana-publish    # THREDDS publication (future)
moana-transfer   # File transfer (future)
```

## Basic Usage

### Process Files with Config File

```bash
moana-qc --config qc_config.yml --cycle ${CYLC_TASK_CYCLE_POINT}
```

### Process Specific Files

```bash
moana-qc \
  --filelist file1.csv file2.csv file3.csv \
  --cycle 20260408T0000 \
  --out-dir /data/obs/mangopare/processed/
```

### Load Files from JSON

```bash
moana-qc \
  --filelist-json /data/obs/mangopare/incoming/filelist.json \
  --cycle 20260408T0000 \
  --config qc_config.yml
```

## Command-Line Options

### Required Options

- `--filelist FILE [FILE ...]`: CSV files to process
- `--filelist-json PATH`: JSON file with file list
- `--config PATH`: YAML configuration file

At least one of `--filelist`, `--filelist-json`, or `--config` (with filelist) must be provided.

### Optional Parameters

- `--cycle DATETIME`: Cycle datetime (ISO or Cylc format YYYYMMDDTHHMM)
- `--out-dir PATH`: Output directory for netCDF files
- `--fishing-metafile PATH`: Fisher metadata CSV file
- `--test-list-1 TEST [TEST ...]`: First batch of QC tests
- `--test-list-2 TEST [TEST ...]`: Second batch of QC tests (stationary gear)

### Logging Options

- `-v, --verbose`: Enable debug logging
- `--log-file PATH`: Write logs to file

### Output Options

- `--output-json PATH`: Write list of successful files to JSON

## Configuration File

Create a YAML file with QC parameters (see [example_qc_config.yml](example_qc_config.yml)):

```yaml
# qc_config.yml
out_dir: "/data/obs/mangopare/processed/%Y%m%d_%Hz/"
status_file_dir: "/data/obs/mangopare/processed/status/"

fishing_metafile: "/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv"

test_list_1:
  - impossible_date
  - impossible_location
  - timing_gap
  - global_range

test_list_2:
  - stationary_position_check
  - temp_drift

save_flags: false
convert_p_to_z: true
```

## Cylc Integration

### In flow.cylc

```yaml
[[qc_and_ingest]]
    script = |
        moana-qc \
            --config /config/cylc-src-ops-test/mangopare/etc/qc_config.yml \
            --cycle ${CYLC_TASK_CYCLE_POINT} \
            --filelist-json /data/obs/mangopare/incoming/filelist_${CYLC_TASK_CYCLE_POINT}.json \
            --output-json /data/obs/mangopare/processed/success_${CYLC_TASK_CYCLE_POINT}.json \
            --log-file /var/log/moana-qc/${CYLC_TASK_CYCLE_POINT}.log \
            --verbose
```

### Environment Variables

Cylc provides several useful environment variables:

- `${CYLC_TASK_CYCLE_POINT}`: Current cycle point (e.g., 20260408T0000Z)
- `${CYLC_TASK_WORK_DIR}`: Task working directory
- `${CYLC_SUITE_RUN_DIR}`: Suite run directory

## Cycle Time Formats

The `--cycle` option accepts multiple formats:

1. **ISO 8601**: `2026-04-08T00:00:00`
2. **Cylc format**: `20260408T0000` or `20260408T0000Z`
3. **Date only**: `20260408` (assumes 00:00:00)
4. **Omitted**: Uses current datetime

## Examples

### Manual Processing

```bash
# Process all CSVs in a directory
moana-qc \
  --filelist /data_exchange/zebratech/incoming/*.csv \
  --config qc_config.yml \
  --out-dir /data/obs/mangopare/processed/ \
  --verbose
```

### Reprocess Historical Data

```bash
# Reprocess with specific cycle time
moana-qc \
  --filelist /archive/mangopare/raw/20250101/*.csv \
  --cycle 2025-01-01T00:00:00 \
  --config qc_config.yml \
  --out-dir /data/obs/mangopare/reprocessed/
```

### Debug Mode

```bash
# Enable verbose logging and save to file
moana-qc \
  --config qc_config.yml \
  --cycle 20260408T0000 \
  --verbose \
  --log-file /tmp/moana-qc-debug.log
```

### Test Configuration

```bash
# Test with a single file
moana-qc \
  --filelist /data/test/MOANA_0001_test.csv \
  --config qc_config.yml \
  --verbose
```

## Output

### Success

Returns exit code `0` and logs:
```
2026-04-08 12:00:00 - moana_qc - INFO - Processing 15 files
2026-04-08 12:01:30 - moana_qc - INFO - Successfully processed 15 files
2026-04-08 12:01:30 - moana_qc - INFO - Wrote success list to /data/obs/mangopare/processed/success_20260408_0000z.json
```

### Partial Success

Returns exit code `1` if some files failed:
```
2026-04-08 12:00:00 - moana_qc - WARNING - No files were successfully processed
```

### Error

Returns exit code `2` on critical error:
```
2026-04-08 12:00:00 - moana_qc - ERROR - QC processing failed: Config file not found
```

## Success File JSON Format

The `--output-json` file contains:

```json
{
  "cycle_dt": "20260408_0000z",
  "total_files": 15,
  "filelist": [
    "/data/obs/mangopare/processed/MOANA_0001_20260408_qc_260408.nc",
    "/data/obs/mangopare/processed/MOANA_0002_20260408_qc_260408.nc"
  ]
}
```

This can be consumed by downstream Cylc tasks (e.g., publication, transfer).

## Tips

1. **Always use `--config`** for production workflows to keep parameters in version control
2. **Use `--verbose`** during development and debugging
3. **Specify `--log-file`** in Cylc tasks for easier troubleshooting
4. **Use `--output-json`** to pass file lists to downstream tasks
5. **Test configurations** with a single file before batch processing

## Troubleshooting

### No files specified

```bash
ERROR - No files specified. Use --filelist or --filelist-json
```

**Solution**: Provide files via `--filelist`, `--filelist-json`, or in `--config`

### Cannot parse cycle time

```bash
ERROR - Cannot parse cycle time: ABC123
```

**Solution**: Use ISO format `2026-04-08T00:00:00` or Cylc format `20260408T0000`

### Config file not found

```bash
ERROR - Config file not found: qc_config.yml
```

**Solution**: Check the path is correct and file exists

### Import errors

```bash
ModuleNotFoundError: No module named 'moana_qc'
```

**Solution**: Reinstall the package: `pip install -e .`

## See Also

- [Cylc Workflow README](/config/cylc-src-ops-test/mangopare/README.md)
- [QC Configuration Example](example_qc_config.yml)
- [Code Modernization Guide](CODE_MODERNIZATION.md)
