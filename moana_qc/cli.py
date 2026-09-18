#!/usr/bin/env python3
"""Unified CLI for Moana/Mangōpare sensor data processing.

Provides subcommands for the complete workflow:
- newfiles: Identify new incoming files
- qc: Run quality control on sensor data  
- publish: Prepare data for THREDDS publication
- transfer: Transfer published data to remote server
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

from moana_qc.wrapper import QcWrapper


def parse_list_arg(value: str | list) -> list[str]:
    """Parse list arguments that may be in Python list format or space-separated.
    
    Handles:
    - Space-separated: 'test1 test2 test3'
    - Python list with brackets: "['test1', 'test2', 'test3']"
    - Single quoted strings with commas: "'test1', 'test2'"
    """
    if isinstance(value, list):
        # Already a list (from config file)
        return value
    
    # Remove brackets if present
    value = value.strip()
    if value.startswith('[') and value.endswith(']'):
        value = value[1:-1]
    
    # Split by commas and clean up quotes and whitespace
    items = []
    for item in re.split(r',\s*', value):
        item = item.strip().strip('"\'')
        if item and item != '[':
            items.append(item)
    
    return items if items else [value]


class ListAction(argparse.Action):
    """Custom action to parse list arguments flexibly."""
    
    def __call__(self, parser, namespace, values, option_string=None):
        # If values is a list with one element that looks like a Python list, parse it
        if isinstance(values, list) and len(values) == 1 and '[' in values[0]:
            # Join all parts and parse as one string
            result = parse_list_arg(' '.join(values))
        elif isinstance(values, list):
            # Flatten and parse each item
            result = []
            for val in values:
                if '[' in val or ',' in val:
                    result.extend(parse_list_arg(val))
                else:
                    result.append(val.strip().strip('"\''))
        else:
            result = parse_list_arg(values)
        
        setattr(namespace, self.dest, result)


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure logging for CLI."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    return logging.getLogger("moana_qc")


def parse_cycle_time(cycle_str: str | None) -> datetime:
    """Parse cycle time from string or use current time.

    Supports ISO format and Cylc format (YYYYMMDDTHHMM).
    """
    if not cycle_str:
        return datetime.now()

    # Try ISO format first
    try:
        return datetime.fromisoformat(cycle_str)
    except ValueError:
        pass

    # Try Cylc format: YYYYMMDDTHHMM or YYYYMMDDTHHMMZ
    try:
        clean_str = cycle_str.rstrip("Z")
        return datetime.strptime(clean_str, "%Y%m%dT%H%M")
    except ValueError:
        pass

    # Try simple YYYYMMDD
    try:
        return datetime.strptime(cycle_str, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(
            f"Cannot parse cycle time: {cycle_str}. Expected ISO format, YYYYMMDDTHHMM, or YYYYMMDD"
        ) from exc


def load_config(config_file: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)
    return config or {}


def qc_main() -> int:
    """QC subcommand entry point."""
    parser = argparse.ArgumentParser(
        description="Moana/Mangōpare sensor data quality control",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/Output
    parser.add_argument("--filelist", nargs="+", help="List of CSV files to process")
    parser.add_argument(
        "--filelist-json", type=Path, help="JSON file containing list of files to process"
    )
    parser.add_argument(
        "--config", type=Path, help="YAML configuration file with processing parameters"
    )
    parser.add_argument("--out-dir", type=Path, help="Output directory for QC netCDF files")

    # Cycle time (from Cylc)
    parser.add_argument("--cycle", help="Cycle datetime (ISO format or YYYYMMDDTHHMM from Cylc)")

    # Metadata
    parser.add_argument("--fishing-metafile", type=Path, help="CSV file with fisher metadata")

    # QC parameters
    parser.add_argument(
        "--test-list-1",
        nargs="+",
        action=ListAction,
        help="First batch of QC tests to run (space-separated or comma-separated list)",
    )
    parser.add_argument(
        "--test-list-2",
        nargs="+",
        action=ListAction,
        help="Second batch of QC tests (for stationary gear; space-separated or comma-separated list)",
    )
    parser.add_argument(
        "--save-flags",
        action="store_true",
        help="Save all individual QC test flags (default: only save summary flags)",
    )

    # Logging
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-file", type=Path, help="Write logs to file")

    # Output format
    parser.add_argument("--output-json", type=Path, help="Write list of successful files to JSON")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose, args.log_file)

    try:
        # Parse cycle time
        cycle_dt = parse_cycle_time(args.cycle)
        logger.info(f"Cycle time: {cycle_dt}")

        # Load configuration
        config = {}
        if args.config:
            logger.info(f"Loading configuration from {args.config}")
            config = load_config(args.config)

        # Command-line args override config file
        wrapper_kwargs = {
            "filelist": args.filelist or config.get("filelist"),
            "out_dir": str(args.out_dir) if args.out_dir else config.get("out_dir"),
            "test_list_1": args.test_list_1 or config.get("test_list_1"),
            "test_list_2": args.test_list_2 or config.get("test_list_2"),
            "fishing_metafile": str(args.fishing_metafile)
            if args.fishing_metafile
            else config.get("fishing_metafile"),
            "save_flags": args.save_flags if args.save_flags else config.get("save_flags", False),
            "logger": logger,
        }

        # Add other config parameters
        for key in [
            "outfile_ext",
            "status_file_ext",
            "status_file_dir",
            "convert_p_to_z",
            "attr_file",
            "gear_class",
        ]:
            if key in config:
                wrapper_kwargs[key] = config[key]

        # Load filelist from JSON if specified
        if args.filelist_json:
            with open(args.filelist_json) as f:
                filelist_data = json.load(f)
                wrapper_kwargs["filelist"] = filelist_data.get("filelist", [])

        # Check we have files to process
        if not wrapper_kwargs.get("filelist"):
            logger.error("No files specified. Use --filelist or --filelist-json")
            return 1

        logger.info(f"Processing {len(wrapper_kwargs['filelist'])} files")

        # Create wrapper and run
        wrapper = QcWrapper(**wrapper_kwargs)
        wrapper.set_cycle(cycle_dt)

        success_files = wrapper.run()

        # Output results
        if success_files:
            logger.info(f"Successfully processed {len(success_files)} files")

            # Optionally write to JSON
            if args.output_json:
                output_data = {
                    "cycle_dt": cycle_dt.strftime("%Y%m%d_%H%Mz"),
                    "total_files": len(success_files),
                    "filelist": success_files,
                }
                args.output_json.parent.mkdir(parents=True, exist_ok=True)
                with open(args.output_json, "w") as f:
                    json.dump(output_data, f, indent=2)
                logger.info(f"Wrote success list to {args.output_json}")

            return 0
        else:
            logger.warning("No files were successfully processed")
            return 1

    except Exception as e:
        logger.exception(f"QC processing failed: {e}")
        return 2


def stats_main() -> int:
    """Stats subcommand entry point."""
    parser = argparse.ArgumentParser(
        description="Generate weekly Mangōpare statistics and plots",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/Output
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Directory containing processed QC'd NetCDF files"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Output directory for statistics and plots (supports strftime)"
    )
    parser.add_argument(
        "--config", type=Path, help="YAML configuration file with processing parameters"
    )

    # Cycle time
    parser.add_argument("--cycle", help="Cycle datetime (ISO format or YYYYMMDDTHHMM)")

    # Plot parameters
    parser.add_argument(
        "--bbox", 
        nargs=4, 
        type=float, 
        help="Bounding box [lon_min, lon_max, lat_min, lat_max]"
    )
    parser.add_argument(
        "--resolution",
        type=float,
        help="Grid resolution for histogram (degrees)"
    )
    parser.add_argument(
        "--lon-offset",
        type=float,
        help="Longitude offset for plotting"
    )
    parser.add_argument(
        "--bounds",
        nargs="+",
        type=float,
        help="Colorbar boundaries for plots"
    )
    parser.add_argument(
        "--kml-output",
        help="KML output filename pattern (supports strftime)"
    )

    # Logging
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-file", type=Path, help="Write logs to file")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose, args.log_file)

    try:
        # Parse cycle time
        cycle_dt = parse_cycle_time(args.cycle)
        logger.info(f"Cycle time: {cycle_dt}")

        # Load configuration
        config = {}
        if args.config:
            logger.info(f"Loading configuration from {args.config}")
            config = load_config(args.config)

        # Command-line args override config file
        wrapper_kwargs = {
            "logger": logger,
        }

        # Set parameters with precedence: CLI args > config > defaults
        if args.data_dir:
            wrapper_kwargs["data_dir"] = str(args.data_dir)
        elif "data_dir" in config:
            wrapper_kwargs["data_dir"] = config["data_dir"]

        if args.out_dir:
            wrapper_kwargs["out_dir"] = str(args.out_dir)
        elif "out_dir" in config:
            wrapper_kwargs["out_dir"] = config["out_dir"]

        if args.bbox:
            wrapper_kwargs["bbox"] = args.bbox
        elif "bbox" in config:
            wrapper_kwargs["bbox"] = config["bbox"]

        if args.resolution:
            wrapper_kwargs["resolution"] = args.resolution
        elif "resolution" in config:
            wrapper_kwargs["resolution"] = config["resolution"]

        if args.lon_offset is not None:
            wrapper_kwargs["lon_offset"] = args.lon_offset
        elif "lon_offset" in config:
            wrapper_kwargs["lon_offset"] = config["lon_offset"]

        if args.bounds:
            wrapper_kwargs["bounds"] = args.bounds
        elif "bounds" in config:
            wrapper_kwargs["bounds"] = config["bounds"]

        if args.kml_output:
            wrapper_kwargs["kml_output"] = args.kml_output
        elif "kml_output" in config:
            wrapper_kwargs["kml_output"] = config["kml_output"]

        # Import and create wrapper
        from moana_qc.stats_and_plots import Wrapper as StatsWrapper

        logger.info("Creating stats wrapper...")
        wrapper = StatsWrapper(**wrapper_kwargs)
        wrapper.set_cycle(cycle_dt)

        # Run statistics and plotting
        logger.info("Generating weekly statistics and plots...")
        wrapper.run()

        logger.info("Successfully generated statistics and plots")
        return 0

    except Exception as e:
        logger.exception(f"Stats generation failed: {e}")
        return 2


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="mangopare",
        description="Moana/Mangōpare sensor data processing workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Identify new files
  mangopare newfiles --newfile-dir /data_exchange/zebratech/incoming \\
                     --old-files-dirs /data/obs/mangopare/processed \\
                     --cycle 20260409T0000

  # Run quality control
  mangopare qc --filelist-json newfiles.json \\
               --out-dir /data/obs/mangopare/processed/ \\
               --cycle 20260409T0000 --save-flags

  # Publish for THREDDS
  mangopare publish --filelist-json success_files.json \\
                    --out-dir /data/obs/mangopare/published/ \\
                    --cycle 20260409T0000

  # Transfer to remote server
  mangopare transfer --filelist-json published_files.json \\
                     --destination user@host:/path/ \\
                     --cycle 20260409T0000

  # Generate weekly statistics and plots
  mangopare stats --data-dir /data/obs/mangopare/processed/ \\
                  --out-dir /data/obs/mangopare/weekly_stats/%Y%m%d_00z/ \\
                  --cycle 20260409T0000

For detailed help on each subcommand:
  mangopare <subcommand> --help
        """,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Create subparsers
    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Available workflow steps",
        dest="subcommand",
        help="Use '<subcommand> --help' for more information",
        required=True,
    )

    # ===== NEWFILES SUBCOMMAND =====
    newfiles_parser = subparsers.add_parser(
        "newfiles",
        help="Identify new incoming files for processing",
        description="Compare incoming files against already-processed files to identify new data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_newfiles_arguments(newfiles_parser)

    # ===== QC SUBCOMMAND =====
    qc_parser = subparsers.add_parser(
        "qc",
        help="Run quality control on sensor data",
        description="Apply quality control tests to raw sensor data and generate QC'd NetCDF files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_qc_arguments(qc_parser)

    # ===== PUBLISH SUBCOMMAND =====
    publish_parser = subparsers.add_parser(
        "publish",
        help="Prepare data for THREDDS publication",
        description="Reformat QC'd data to THREDDS-compatible CF-compliant NetCDF.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_publish_arguments(publish_parser)

    # ===== TRANSFER SUBCOMMAND =====
    transfer_parser = subparsers.add_parser(
        "transfer",
        help="Transfer published data to remote server",
        description="Upload published NetCDF files to THREDDS server via rsync.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_transfer_arguments(transfer_parser)

    # ===== STATS SUBCOMMAND =====
    stats_parser = subparsers.add_parser(
        "stats",
        help="Generate weekly statistics and plots",
        description="Generate spatial plots and KML files comparing Mangōpare and Argo data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_stats_arguments(stats_parser)

    return parser


def add_newfiles_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the newfiles subcommand."""
    parser.add_argument("--newfile-dir", type=Path, required=True, help="Directory containing new incoming files")
    parser.add_argument("--old-files-dirs", nargs="+", type=Path, required=True, help="Directory or directories with already processed files")
    parser.add_argument("--files-to-append", nargs="+", help="Additional specific files to include")
    parser.add_argument("--cutoff", type=int, default=7, help="Days to search backward")
    parser.add_argument("--file-format", default="*.csv", help="Glob pattern for files")
    parser.add_argument("--maxfiles", type=int, default=500, help="Maximum files to process")
    parser.add_argument("--override-max-files", action="store_true", help="Allow exceeding maxfiles")
    parser.add_argument("--outfile", type=Path, help="Output text file (supports strftime)")
    parser.add_argument("--output-json", type=Path, help="Output JSON file")
    parser.add_argument("--cycle", help="Cycle datetime (ISO/YYYYMMDDTHHMM)")
    parser.add_argument("--end-date", help="End date for search")
    parser.add_argument("--config", type=Path, help="YAML configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--log-file", type=Path, help="Log file path")


def add_qc_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the qc subcommand."""
    parser.add_argument("--filelist", nargs="+", help="List of CSV files to process")
    parser.add_argument("--filelist-json", type=Path, help="JSON file with file list")
    parser.add_argument("--config", type=Path, help="YAML configuration file")
    parser.add_argument("--out-dir", type=Path, help="Output directory for QC files")
    parser.add_argument("--cycle", help="Cycle datetime (ISO/YYYYMMDDTHHMM)")
    parser.add_argument("--fishing-metafile", type=Path, help="CSV with fisher metadata")
    parser.add_argument("--test-list-1", nargs="+", action=ListAction, help="First batch of QC tests (space or comma separated)")
    parser.add_argument("--test-list-2", nargs="+", action=ListAction, help="Second batch of QC tests (space or comma separated)")
    parser.add_argument("--save-flags", action="store_true", help="Save all QC test flags")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    parser.add_argument("--output-json", type=Path, help="JSON file for successful files")


def add_publish_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the publish subcommand."""
    parser.add_argument("--filelist", nargs="+", help="List of QC'd NetCDF files")
    parser.add_argument("--filelist-json", type=Path, help="JSON file with file list")
    parser.add_argument("--config", type=Path, help="YAML configuration file")
    parser.add_argument("--out-dir", type=Path, help="Output directory for published files")
    parser.add_argument("--status-file-dir", type=Path, help="Directory for status files")
    parser.add_argument("--cycle", help="Cycle datetime (ISO/YYYYMMDDTHHMM)")
    parser.add_argument("--outfile-ext", default="_published", help="Filename extension")
    parser.add_argument("--attr-file", type=Path, help="YAML file with attributes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    parser.add_argument("--output-json", type=Path, help="JSON file for published files")


def add_transfer_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the transfer subcommand."""
    parser.add_argument("--filelist", nargs="+", help="List of files to transfer")
    parser.add_argument("--filelist-json", type=Path, help="JSON file with file list")
    parser.add_argument("--config", type=Path, help="YAML configuration file")
    parser.add_argument("--key-file", type=Path, default="/home/metocean/.ssh/id_rsa", help="SSH private key path")
    parser.add_argument("--destination", default="metocean@dataserv1.hm:/data/moana/Mangopare/public/", help="Remote destination (user@host:/path/)")
    parser.add_argument("--cycle", help="Cycle datetime (ISO/YYYYMMDDTHHMM)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    parser.add_argument("--dry-run", action="store_true", help="Show files without transferring")


def add_stats_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the stats subcommand."""
    parser.add_argument("--data-dir", type=Path, default="/data/obs/mangopare/processed/", help="Directory containing processed QC'd NetCDF files")
    parser.add_argument("--out-dir", type=Path, help="Output directory for statistics and plots (supports strftime)")
    parser.add_argument("--config", type=Path, help="YAML configuration file")
    parser.add_argument("--cycle", help="Cycle datetime (ISO/YYYYMMDDTHHMM)")
    parser.add_argument("--bbox", nargs=4, type=float, help="Bounding box [lon_min, lon_max, lat_min, lat_max]")
    parser.add_argument("--resolution", type=float, default=1, help="Grid resolution for histogram (degrees)")
    parser.add_argument("--lon-offset", type=float, default=180, help="Longitude offset for plotting")
    parser.add_argument("--bounds", nargs="+", type=float, help="Colorbar boundaries for plots")
    parser.add_argument("--kml-output", default="mangopare_deployments_%Y%m%d.kml", help="KML output filename pattern (supports strftime)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--log-file", type=Path, help="Log file path")


def main() -> int:
    """Main entry point for the unified mangopare CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Import main functions from other modules
    from moana_qc.newfiles import main as newfiles_main
    from moana_qc.publish import main as publish_main
    from moana_qc.transfer import main as transfer_main

    # Dispatch to appropriate subcommand
    # Modify sys.argv to match what each subcommand's main() expects
    if args.subcommand == "newfiles":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return newfiles_main()
    elif args.subcommand == "qc":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return qc_main()
    elif args.subcommand == "publish":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return publish_main()
    elif args.subcommand == "transfer":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return transfer_main()
    elif args.subcommand == "stats":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return stats_main()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
