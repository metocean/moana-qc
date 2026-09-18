# Moana QC CLI Commands

This document describes the four main CLI commands for the Moana QC workflow.

## Installation

After making changes to the package, install it in editable mode:

```bash
cd /source/moana-qc
pip install -e .
```

## 1. moana-newfiles - Identify New Files for Processing

Identifies new incoming sensor data files that haven't been processed yet.

### Basic Usage

```bash
moana-newfiles \
  --newfile-dir /data_exchange/zebratech/incoming \
  --old-files-dirs /data/obs/mangopare/processed /data/obs/mangopare/raw \
  --output-json /data/obs/mangopare/filelists/newfiles_%Y%m%d_%H00z.json \
  --cycle 20260409T0000
```

### Key Parameters

- `--newfile-dir`: Directory containing new incoming files
- `--old-files-dirs`: One or more directories with already processed files
- `--cutoff`: Days backward from cycle time to search (default: 7)
- `--file-format`: Glob pattern for matching files (default: `*.csv`)
- `--maxfiles`: Maximum files to process (default: 500)
- `--output-json`: Save list as JSON with metadata
- `--outfile`: Save list as plain text (supports strftime formatting)
- `--cycle`: Cycle datetime from Cylc workflow

### Example Output (JSON)

```json
{
  "cycle_dt": "20260409_0000z",
  "total_files": 4,
  "filelist": [
    "/data_exchange/zebratech/incoming/MOANA_0072_181_260408225009.csv",
    "/data_exchange/zebratech/incoming/MOANA_0329_707_260408223027.csv"
  ]
}
```

---

## 2. moana-qc - Quality Control Processing

Runs quality control tests on raw sensor data and produces QC'd NetCDF files.

### Basic Usage

```bash
moana-qc \
  --filelist-json /data/obs/mangopare/filelists/newfiles_20260409_0000z.json \
  --out-dir /data/obs/mangopare/processed/ \
  --cycle 20260409T0000 \
  --fishing-metafile /data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv \
  --test-list-1 impossible_date impossible_location impossible_speed timing_gap global_range \
  --test-list-2 start_end_dist_check \
  --save-flags \
  -v
```

### Key Parameters

- `--filelist`: List of CSV files to process (space-separated)
- `--filelist-json`: JSON file with list of files (from moana-newfiles)
- `--out-dir`: Output directory for QC NetCDF files
- `--fishing-metafile`: CSV file with fisher metadata
- `--test-list-1`: First batch of QC tests (independent tests)
- `--test-list-2`: Second batch (tests that depend on test-list-1)
- `--save-flags`: Save all individual QC test flags
- `--output-json`: Save list of successfully processed files
- `--cycle`: Cycle datetime from Cylc workflow

### Available QC Tests

**test-list-1** (independent tests):
- `impossible_date`
- `impossible_location`
- `impossible_speed`
- `timing_gap`
- `global_range`
- `remove_ref_location`
- `spike`
- `temp_drift`
- `stationary_position_check`
- `reset_code_check`
- `check_timestamp_overflow`

**test-list-2** (dependent tests):
- `start_end_dist_check` (requires stationary position data)

### Example Output

The command generates:
- QC'd NetCDF files in `--out-dir`
- Status CSV file: `status_file_YYYYMMDD.csv`
- Success list JSON: `filelist/success_files_list_YYYYMMDD_HH00z.json`

---

## 3. moana-publish - Prepare Data for THREDDS Publication

Reformats QC'd data to THREDDS-compatible CF-compliant NetCDF for public access.

### Basic Usage

```bash
moana-publish \
  --filelist-json /data/obs/mangopare/processed/filelist/success_files_list_20260409_0000z.json \
  --out-dir /data/obs/mangopare/published/ \
  --status-file-dir /data/obs/mangopare/processed/ \
  --cycle 20260409T0000 \
  --outfile-ext _published \
  -v
```

### Key Parameters

- `--filelist`: List of QC'd NetCDF files to publish
- `--filelist-json`: JSON file with list of files (from moana-qc)
- `--out-dir`: Output directory for published NetCDF files
- `--status-file-dir`: Directory for status files
- `--outfile-ext`: Extension for published files (default: `_published`)
- `--attr-file`: YAML file with publication attributes
- `--output-json`: Save list of published files
- `--cycle`: Cycle datetime from Cylc workflow

### Publication Criteria

Only files that meet these criteria are published:
- `public` attribute is `TRUE`
- First measurement is after `publication_date`

### Example Output

The command generates:
- Published NetCDF files with CF-1.6 conventions
- Success list JSON: `filelist/published_files_list_YYYYMMDD_HH00z.json`

---

## 4. moana-transfer - Transfer Data to THREDDS Server

Transfers published NetCDF files to a remote THREDDS server using rsync over SSH.

### Basic Usage

```bash
moana-transfer \
  --filelist-json /data/obs/mangopare/processed/filelist/published_files_list_20260409_0000z.json \
  --destination metocean@dataserv1.hm:/data/moana/Mangopare/public/ \
  --key-file /home/metocean/.ssh/id_rsa \
  --cycle 20260409T0000 \
  -v
```

### Key Parameters

- `--filelist`: List of published NetCDF files to transfer
- `--filelist-json`: JSON file with list of files (from moana-publish)
- `--destination`: Remote server path (rsync format: `user@host:/path/`)
- `--key-file`: SSH private key for authentication
- `--dry-run`: Preview files without transferring
- `--cycle`: Cycle datetime from Cylc workflow

### Dry Run Mode

Test the transfer without actually moving files:

```bash
moana-transfer \
  --filelist-json /data/obs/mangopare/processed/filelist/published_files_list_20260409_0000z.json \
  --destination metocean@dataserv1.hm:/data/moana/Mangopare/public/ \
  --dry-run \
  -v
```

### Transfer Method

Uses `rsync` with the following flags:
- `-a`: Archive mode (preserve permissions, timestamps)
- `-v`: Verbose output
- `-P`: Show progress and keep partial files
- `-e ssh`: Use SSH with specified key file

---

## Complete Workflow Example

```bash
# Step 1: Identify new files
moana-newfiles \
  --newfile-dir /data_exchange/zebratech/incoming \
  --old-files-dirs /data/obs/mangopare/processed \
  --output-json /data/obs/mangopare/newfiles.json \
  --cycle 20260409T0000

# Step 2: Run QC processing
moana-qc \
  --filelist-json /data/obs/mangopare/newfiles.json \
  --out-dir /data/obs/mangopare/processed/ \
  --cycle 20260409T0000 \
  --fishing-metafile /data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv \
  --test-list-1 impossible_date impossible_location impossible_speed timing_gap global_range \
  --test-list-2 start_end_dist_check \
  --save-flags

# Step 3: Publish data for THREDDS
moana-publish \
  --filelist-json /data/obs/mangopare/processed/filelist/success_files_list_20260409_0000z.json \
  --out-dir /data/obs/mangopare/published/ \
  --cycle 20260409T0000

# Step 4: Transfer to THREDDS server
moana-transfer \
  --filelist-json /data/obs/mangopare/processed/filelist/published_files_list_20260409_0000z.json \
  --destination metocean@dataserv1.hm:/data/moana/Mangopare/public/ \
  --cycle 20260409T0000
```

---

## Using Configuration Files

All commands support YAML configuration files to avoid long command lines:

### newfiles_config.yml
```yaml
newfile_dir: /data_exchange/zebratech/incoming
old_files_dirs:
  - /data/obs/mangopare/processed
  - /data/obs/mangopare/raw
cutoff: 7
file_format: "*.csv"
maxfiles: 500
```

### qc_config.yml
```yaml
out_dir: /data/obs/mangopare/processed/
fishing_metafile: /data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv
test_list_1:
  - impossible_date
  - impossible_location
  - impossible_speed
  - timing_gap
  - global_range
test_list_2:
  - start_end_dist_check
save_flags: true
```

### publish_config.yml
```yaml
out_dir: /data/obs/mangopare/published/
status_file_dir: /data/obs/mangopare/processed/
outfile_ext: _published
```

### transfer_config.yml
```yaml
destination: metocean@dataserv1.hm:/data/moana/Mangopare/public/
key_file: /home/metocean/.ssh/id_rsa
```

### Usage with Config Files

```bash
moana-newfiles --config newfiles_config.yml --cycle 20260409T0000
moana-qc --config qc_config.yml --filelist-json newfiles.json --cycle 20260409T0000
moana-publish --config publish_config.yml --filelist-json success.json --cycle 20260409T0000
moana-transfer --config transfer_config.yml --filelist-json published.json --cycle 20260409T0000
```

---

## Cylc Integration

These CLIs are designed for Cylc workflows where `--cycle` is provided by the scheduler:

```python
[[process_new_data]]
    script = """
        moana-newfiles \
          --config $CONFIG_DIR/newfiles.yml \
          --cycle $CYLC_TASK_CYCLE_POINT \
          --output-json $OUTPUT_DIR/newfiles_${CYLC_TASK_CYCLE_POINT}.json
    """

[[qc_data]]
    script = """
        moana-qc \
          --config $CONFIG_DIR/qc.yml \
          --filelist-json $OUTPUT_DIR/newfiles_${CYLC_TASK_CYCLE_POINT}.json \
          --cycle $CYLC_TASK_CYCLE_POINT
    """

[[publish_data]]
    script = """
        moana-publish \
          --config $CONFIG_DIR/publish.yml \
          --filelist-json $OUTPUT_DIR/success_files_list_${CYLC_TASK_CYCLE_POINT}.json \
          --cycle $CYLC_TASK_CYCLE_POINT
    """

[[transfer_data]]
    script = """
        moana-transfer \
          --config $CONFIG_DIR/transfer.yml \
          --filelist-json $OUTPUT_DIR/published_files_list_${CYLC_TASK_CYCLE_POINT}.json \
          --cycle $CYLC_TASK_CYCLE_POINT
    """
```

---

## Logging

All commands support:
- `-v` or `--verbose`: Enable debug logging
- `--log-file PATH`: Write logs to file

Example:
```bash
moana-qc --config qc.yml --cycle 20260409T0000 -v --log-file /var/log/moana/qc.log
```
