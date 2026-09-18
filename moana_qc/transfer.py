"""Transfer module for moving QC'd data to THREDDS servers."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import xarray as xr
import yaml

xr.set_options(keep_attrs=True)


class Wrapper:
    """Transfer observational data to THREDDS servers.

    Transfers QC'd netCDF files from local storage to THREDDS server.

    Args:
        filelist: List of file paths to transfer
        filelist_json: Path to JSON file containing file list
        key_file: SSH private key path for server authentication
        destination: Remote server destination path
        logger: Logger instance

    Note:
        Files are transferred using rsync over SSH.
    """

    def __init__(
        self,
        filelist: list[str] | None = None,
        filelist_json: str | None = None,
        key_file: str = "/home/metocean/.ssh/id_rsa",
        destination: str = "metocean@dataserv1.hm:/data/moana/Mangopare/public/",
        logger: logging.Logger = logging.getLogger(__name__),
        **kwargs,
    ):
        # Extract filelist from config if passed via kwargs (from linked parent tasks)
        if filelist is None and "config" in kwargs:
            filelist = kwargs["config"].get("filelist")
            if filelist:
                logger.info(f"Extracted filelist from config kwargs: {len(filelist)} files")

        self.filelist = filelist
        self.filelist_json = filelist_json
        self.key_file = Path(key_file)
        self.destination = destination
        self.logger = logger
        self.cycle_dt: datetime | None = None

    def set_cycle(self, cycle_dt: datetime) -> None:
        """Set the cycle datetime for this transfer run."""
        self.cycle_dt = cycle_dt

    def _set_filelist(self) -> None:
        """Load file list from JSON file if not provided directly.

        Supports multiple JSON keys: 'published_files', 'filelist', 'success_files'.
        """
        if not self.filelist and self.filelist_json:
            # Format the path with cycle_dt if available
            json_path_str = (
                self.cycle_dt.strftime(self.filelist_json) if self.cycle_dt else self.filelist_json
            )
            json_path = Path(json_path_str)

            try:
                data = json.loads(json_path.read_text())
                # Support multiple key names for backward compatibility
                self.filelist = (
                    data.get("published_files")
                    or data.get("filelist")
                    or data.get("success_files", [])
                )
                self.logger.info(f"Loaded {len(self.filelist)} files from {json_path}")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.logger.error(f"Could not read filelist JSON {json_path}: {e}")

        if not self.filelist:
            self.logger.warning("No file list found. No transfer will be performed.")

    def run(self) -> None:
        """Execute the file transfer.

        Transfers all files in the filelist to the destination server using rsync.

        Raises:
            subprocess.CalledProcessError: If rsync command fails
            ValueError: If no files are available to transfer
        """
        # Set cycle time to current UTC time if not already set
        if not self.cycle_dt:
            self.set_cycle(datetime.now(timezone.utc))

        self._set_filelist()

        if not self.filelist:
            raise ValueError("No files available to transfer")

        # Transfer each file using rsync
        for file_path in self.filelist:
            self._transfer_file(file_path)

    def _transfer_file(self, file_path: str) -> None:
        """Transfer a single file using rsync.

        Args:
            file_path: Path to the file to transfer

        Raises:
            subprocess.CalledProcessError: If rsync fails
        """
        # Build rsync command as list (secure - no shell injection)
        rsync_cmd = [
            "rsync",
            "-av",
            "-P",
            "-e",
            f"ssh -i {self.key_file}",
            file_path,
            self.destination,
        ]

        try:
            result = subprocess.run(rsync_cmd, check=True, capture_output=True, text=True)
            self.logger.info(f"Successfully transferred: {file_path}")
            if result.stdout:
                self.logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to transfer {file_path}: {e.stderr}")
            raise


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure logging for the transfer CLI."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers, force=True)
    return logging.getLogger(__name__)


def parse_cycle_time(cycle_str: str | None) -> datetime:
    """Parse cycle time from various formats."""
    if cycle_str is None:
        return datetime.now(timezone.utc)

    # Try ISO format first
    try:
        return datetime.fromisoformat(cycle_str)
    except ValueError:
        pass

    # Try Cylc format: YYYYMMDDTHHMM or YYYYMMDDTHHMMz
    try:
        clean_str = cycle_str.rstrip("Zz")
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


def main() -> int:
    """Main CLI entry point for moana-transfer."""
    parser = argparse.ArgumentParser(
        description="Transfer Moana/Mangōpare published data to THREDDS server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input
    parser.add_argument(
        "--filelist",
        nargs="+",
        help="List of published NetCDF files to transfer",
    )
    parser.add_argument(
        "--filelist-json",
        type=Path,
        help="JSON file containing list of files to transfer (e.g., from moana-publish output)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML configuration file with transfer parameters",
    )

    # Transfer parameters
    parser.add_argument(
        "--key-file",
        type=Path,
        default="/home/metocean/.ssh/id_rsa",
        help="SSH private key path for server authentication",
    )
    parser.add_argument(
        "--destination",
        default="metocean@dataserv1.hm:/data/moana/Mangopare/public/",
        help="Remote server destination path (rsync format: user@host:/path/)",
    )

    # Cycle time (from Cylc)
    parser.add_argument(
        "--cycle",
        help="Cycle datetime (ISO format or YYYYMMDDTHHMM from Cylc)",
    )

    # Logging
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Write logs to file",
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show files that would be transferred without actually transferring them",
    )

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
            with open(args.config) as f:
                config = yaml.safe_load(f) or {}

        # Command-line args override config file
        wrapper_kwargs = {
            "filelist": args.filelist or config.get("filelist"),
            "filelist_json": str(args.filelist_json)
            if args.filelist_json
            else config.get("filelist_json"),
            "key_file": str(args.key_file) if args.key_file else config.get("key_file"),
            "destination": args.destination or config.get("destination"),
            "logger": logger,
        }

        # Check we have files to transfer
        if not wrapper_kwargs.get("filelist") and not wrapper_kwargs.get("filelist_json"):
            logger.error("No files specified. Use --filelist or --filelist-json")
            return 1

        logger.info("Initializing transfer wrapper...")

        # Create wrapper
        wrapper = Wrapper(**wrapper_kwargs)
        wrapper.set_cycle(cycle_dt)

        # Load filelist
        wrapper._set_filelist()

        if not wrapper.filelist:
            logger.warning("No files to transfer")
            return 0

        # Show files
        logger.info(f"Files to transfer: {len(wrapper.filelist)}")
        for file_path in wrapper.filelist:
            logger.info(f"  - {file_path}")

        # Dry run or actual transfer
        if args.dry_run:
            logger.info("DRY RUN - No files were transferred")
            return 0

        # Execute transfer
        logger.info(f"Transferring {len(wrapper.filelist)} files to {wrapper.destination}")
        wrapper.run()

        logger.info("Transfer completed successfully")
        return 0

    except ValueError as e:
        logger.error(f"Transfer failed: {e}")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Transfer command failed: {e}")
        return 2
    except Exception as e:
        logger.exception(f"Unexpected error during transfer: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
