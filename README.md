<a id="page-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/metocean/moana-qc">
    <img src="images/logo.png" alt="Logo" width="260" height="260">
  </a>

<h3 align="center">Moana TD Sensor Quality Control and Processing</h3>

  <p align="center">
    This library contains code to perform the operational, near real-time quality-control and processing of <a href="https://www.moanaproject.org/temperature-sensors">Mangōpare/Moana oceanographic observation data</a>, initially deveoped as part of the <a href="https://www.moanaproject.org/">Moana Project</a> with technology partner <a href="https://www.zebra-tech.co.nz/moana/">ZebraTech</a>.
    <br />
    <br />
    <a href="https://github.com/metocean/moana-qc/blob/master/docs/"><strong>Documentation »</strong></a>
    <br />
  </p>
</div>

<p align="center">
  <img src="https://img.shields.io/github/contributors/metocean/moana-qc">
  <img src="https://img.shields.io/github/issues/metocean/moana-qc">
  <img src="https://img.shields.io/github/actions/workflow/status/metocean/moana-qc/build_test_push.yml?label=Build%20Test">
  <img src="https://img.shields.io/github/license/metocean/moana-qc">
  <a href="https://zenodo.org/badge/latestdoi/295919031"><img src="https://zenodo.org/badge/295919031.svg"></a>
</p>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-programme">About The Programme</a>
      <ul>
        <li><a href="#quality-control-and-processing">Quality Control and Processing</a></li>
        <li><a href="#code-structure">Code Structure</a></li>
        <li><a href="#publically-available-files">Publically Available Files</a></li>
      </ul>
    </li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#development">Development</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#references">References</a></li>
    <li><a href="#licensing">Licensing</a></li>
    <li><a href="#attribution_statement">Attribution Statement</a></li>
    <li><a href="#community">Community</a></li>
  </ol>
</details>
<br />


# About The Programme
This library contains code intended for the operational, near real-time quality-control of [Mangōpare/Moana oceanographic observation data](https://www.zebra-tech.co.nz/moana/).  Only automatic quality control is included at this time, for use with measurements transmitted in near real-time.  For more information on the [Moana Project](https://www.moanaproject.org/temperature-sensors)'s Mangōpare sensor programme, see [Jakoboski et. al (2024)](https://doi.org/10.1016/j.pocean.2024.103278), contact info@moanaproject.org, or visit the websites above.

The current versions are for the purpose of quality-controlling data from the Moana Project's Mangopare (Te Tiro Moana) Mangōpare/Moana temperature and pressure sensor, but will be made more generic if needed.

<p align="right">(<a href="#page-top">back to top</a>)</p>

## Quality Control and Processing

Standard in-situ oceagraphic measurement quality control tests are applied to Mangōpare/Moana observations.  Please see the [docs](https://github.com/metocean/moana-qc/blob/master/docs/) for details on [quality control tests](https://github.com/metocean/moana-qc/blob/master/docs/moana_sensor_qc.md) and [data processing](https://github.com/metocean/moana-qc/blob/master/docs/sensor_processing.md).

<p align="right">(<a href="#page-top">back to top</a>)</p>

## Code Structure

- wrapper.py is the highest level class, which coordinates all the others.  Within it, the user specifies the data reader, the metadata reader, a preprocessor, and the qc_class.
- Data reader: reads the observations in each sensor offload file, formats variable names, and loads global attributes from the file header.
- Metadata reader: right now, reads a spreadsheet with fisher metadata, including whether the sensor is stationary or mobile.
- Preprocessor: very Mangopare specific, mostly does position processing.  Also adds variable attributes from attribute file specified in wrapper.py and finds the "bottom" data points for fishing data.
- QC class: specifies the class that actually applies the QC tests after reading and preprocessing the data.

Defaults for the above are included in wrapper.py in case none are specified.

Currently, the data and metadata readers are both classes in readers.py.

"Standard" oceanographic QC tests for temperature and pressure data are included in qc_tests_df.py.  Most of these are based on QARTOD or Argo tests.  If any new tests are needed, that is most likely the best place to put them.  For each test, a quality flag is assigned.  The tests from qc_test_df.py that should be included in a quality-control run are specified in warpper.py under the variable name `test_list`.  This variable is passed to apply_qc.py where each test is run.  See qc_tests_df.py documentation for lists of possible test names.  Some tests generally work well, others currently not at all.  This is indicated in the qc_tests_df.py docstring.

<p align="right">(<a href="#page-top">back to top</a>)</p>

## Publically Available Files

(Mangōpare Specific)
Two columns have been added to the Mangōpare metadata (Public, Publication Date). The first column "Public" especifies if the data is available for the Public or not (boolean, True or False). If True, the second column "Publication Date" especifies the date when the sharing data agreement was signed.   

Publication functionality is available via the `mangopare publish` command.

Relevant files are located in the THREDDS folder: 
- THREDDS/attribute_list.yml : All the information related to the variables, coordinates, dimensions and global attributes. 
- THREDDS/transfer.public.mangopare.yml : Config file to use for operational deployment.

If you use the publically available data, please cite the Zenodo reference for the dataset: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10420342.svg)](https://doi.org/10.5281/zenodo.10420342)

Please see [THREDDS_README.md](https://github.com/metocean/moana-qc/blob/master/moana_qc/THREDDS/THREDDS_README.ipynb) for more information.

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Installation

This repository contains the `moana-qc` Python package for quality control and processing of Moana/Mangōpare sensor data.

## Requirements

- Python 3.10 or later
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

## Installation with uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package
uv pip install -e .

# Or for development with all tools
uv pip install -e ".[dev]"
```

## Installation with pip

```bash
# Install from source
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## For Cylc Workflows

The package is designed to work with Cylc workflows using virtual environments:

```bash
# In your workflow setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e /source/moana-qc
```

See the [Cylc mangopare workflow documentation](/config/cylc-src-ops-test/mangopare/README.md) for integration details.

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Usage

The package provides a unified `mangopare` command-line interface for the complete data processing workflow:

## Quick Start

```bash
# View all available commands
mangopare --help

# Get help for a specific subcommand
mangopare qc --help
```

## Workflow Commands

### 1. Identify New Files

```bash
mangopare newfiles \
  --newfile-dir /data_exchange/zebratech/incoming \
  --old-files-dirs /data/obs/mangopare/processed \
  --output-json newfiles.json \
  --cycle 20260409T0000
```

### 2. Run Quality Control

```bash
mangopare qc \
  --filelist-json newfiles.json \
  --out-dir /data/obs/mangopare/processed/ \
  --cycle 20260409T0000 \
  --fishing-metafile /data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv \
  --test-list-1 impossible_date impossible_location impossible_speed timing_gap global_range \
  --test-list-2 start_end_dist_check \
  --save-flags \
  --verbose
```

### 3. Publish for THREDDS

```bash
mangopare publish \
  --filelist-json success_files_list.json \
  --out-dir /data/obs/mangopare/published/ \
  --cycle 20260409T0000 \
  --attr-file moana_qc/THREDDS/attribute_list.yml
```

### 4. Transfer to Remote Server

```bash
mangopare transfer \
  --filelist-json published_files_list.json \
  --destination metocean@dataserv1.hm:/data/moana/Mangopare/public/ \
  --cycle 20260409T0000
```

## Using Configuration Files

For simpler command lines, use YAML configuration files:

```bash
# QC with config file
mangopare qc --config qc_config.yml --cycle 20260409T0000

# Publish with config file
mangopare publish --config publish_config.yml --cycle 20260409T0000
```

Example `qc_config.yml`:
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

## Legacy Commands

For backward compatibility, individual commands are still available:
- `moana-newfiles` (same as `mangopare newfiles`)
- `moana-qc` (same as `mangopare qc`)
- `moana-publish` (same as `mangopare publish`)
- `moana-transfer` (same as `mangopare transfer`)

See [CLI_COMMANDS.md](CLI_COMMANDS.md) for detailed documentation of all commands and options.

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Development

For contributing, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Docker Images

The repository includes Dockerfiles for containerized deployment:

### External/Public Use

```bash
docker build -f Dockerfile -t moana-qc .
docker run -ti -v /source:/source -v /data:/data moana-qc:latest
```

### MetOcean Internal Operations

For MetOcean operational use with internal dependencies:

```bash
docker build -f Dockerfile_MOS --no-cache --build-arg GIT_TOKEN=${GIT_TOKEN} -t metocean/moana-qc:latest .
docker run -ti -v /source:/source -v /data:/data metocean/moana-qc:latest
```

The `/data` directory should contain sensor data and will be used for outputs. Add additional directories with `-v` flags as needed.

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Contributing

We welcome contributions! This is an open-source project for oceanographic data quality control.

**Development Branch**: The `cylc` branch contains the modernized codebase for use with Cylc workflows and modern Python tooling.

**Legacy Branch**: The `master` branch maintains backwards compatibility with existing scheduler systems.

To contribute:

1. Fork the Project
2. Create a new Feature Branch (`git checkout -b feature/YourNewFeature`)
3. Commit your Changes (`git commit -m 'Descriptive Comment'`)
4. Push to the Branch (`git push origin feature/YourNewFeature`)
5. Open a Pull Request

<p align="right">(<a href="#page-top">back to top</a>)</p>

# References

For more an in-depth description of the Mangōpare sensor programme:

Jakoboski J, Roughan M, Radford J, de Souza JMAC, Felsing M, Smith R, Puketapu-Waite N, Montaño Orozco M, Maxwell KH, and Van Vranken C (2024)  Partnering with the commercial fishing sector and Aotearoa New Zealand’s ocean community to develop a nationwide subsurface temperature monitoring program, Progress in Oceanography, 103278. doi: [https://doi.org/10.1016/j.pocean.2024.103278](https://doi.org/10.1016/j.pocean.2024.103278)

For a description of the cross-disciplinary context of the Moana Project:

Souza JMAC, Felsing M, Jakoboski J, Gardner JPA and Hudson M (2023) Moana Project: lessons learned from a national scale transdisciplinary research project. Front. Mar. Sci. 10:1322194. doi: [10.3389/fmars.2023.1322194](https://www.frontiersin.org/articles/10.3389/fmars.2023.1322194/full)

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Licensing

Please see [LICENSE.md](https://github.com/metocean/moana-qc/blob/master/LICENSE.md) for the license under which this code can be shared.  Please consider contributing to the code under this repository whenever possible rather then forking or cloning into a new repository so all can benefit from collaborative work.  If you need to fork/clone into a new repository, please let us know so we can include any new developments as a community.

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Attribution Statement

Original code base by MetOcean Solutions, a Division of Meteorological Service of New Zealand Ltd, developed as part of the Moana Project. The Moana Project is funded by the New Zealand Ministry of Business, Innovation, and Employment (MBIE) Endeavour Fund.

The Mangōpare sensor and deck unit hardware were developed by Zebra-Tech, Ltd, Nelson, New Zealand as part of the Moana Project.  Sensors are available through [ZebraTech](https://www.zebra-tech.co.nz/).

<p align="right">(<a href="#page-top">back to top</a>)</p>

# Community

A fishing vessel, in-situ ocean observing quality control working group is in development through [FVON](https://fvon.org/).  Please contact either the Moana Project (info@moanaproject.org) or FVON (through their website) for more information.

<p align="right">(<a href="#page-top">back to top</a>)</p>


