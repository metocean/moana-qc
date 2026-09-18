"""Module for listing new incoming sensor data files."""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml


class ListIncomingFiles:
    """List new files for processing.

    Compares already-transferred files to newly modified files in data exchange directory.
    Calculates which new files should be processed.

    Designed for use in Cylc workflows where cycle_dt is provided by the workflow.

    Args:
        newfile_dir: Directory containing new incoming files
        old_files_dirs: Directory or list of directories with already processed files
        files_to_append: Additional files to include
        cutoff: Days backward from end_date to search for files
        file_format: Glob pattern for file matching (e.g., '*.csv')
        outfile: Output file path (supports strftime formatting)
        end_date: End date for file search (if None, uses current time)
        maxfiles: Maximum number of files to process
        override_max_files: Allow exceeding maxfiles limit
        logger: Logger instance
    """

    def __init__(
        self,
        newfile_dir,
        old_files_dirs,
        files_to_append=None,
        cutoff=7,
        file_format="*.csv",
        outfile=None,
        end_date=None,
        maxfiles=500,
        override_max_files=False,
        logger=logging,
        **kwargs,
    ):
        self.newfile_dir = newfile_dir
        self.old_files_dirs = (
            old_files_dirs if isinstance(old_files_dirs, list) else [old_files_dirs]
        )
        self.files_to_append = files_to_append
        self.cutoff = cutoff
        self.outfile = outfile
        self.end_date = end_date
        self.logger = logger
        self.file_format = file_format
        self.maxfiles = maxfiles
        self.override_max_files = override_max_files
        # cycle_dt should be passed from Cylc workflow, not auto-generated
        self.cycle_dt: datetime | None = None

    #    def set_cycle(self, cycle_dt):
    #        self.cycle_dt = cycle_dt
    #        if self.outfile:
    #            self.outfile = cycle_dt.strftime(self.outfile)

    def set_cycle(self, cycle_dt: datetime) -> None:
        """Set the cycle datetime (typically from Cylc workflow)."""
        self.cycle_dt = cycle_dt

    def _set_times(self):
        if not self.end_date:
            self.end_date = self.cycle_dt
        self.start_date = self.end_date - timedelta(self.cutoff)

    def _check_dirs(self):
        if not self.newfile_dir:
            self.logger.error("New file directory not specified.")
            raise Exception
        if not self.old_files_dirs:
            self.logger.error("Old file directory not specified.")
            raise Exception

    def _list_transferred_files(self):
        """Get set of already-transferred file basenames for O(1) lookup."""
        transferred_files = set()
        for dirname in self.old_files_dirs:
            files_in_dir = glob.glob(os.path.join(dirname, self.file_format), recursive=True)
            transferred_files.update(os.path.basename(fname) for fname in files_in_dir)
        return transferred_files

    def _list_incoming_files(self):
        incoming_files = []
        indir = os.path.join(self.newfile_dir, self.file_format)
        self.logger.info(f"Looking for new files in {indir}...")
        files_in_dir = glob.glob(indir, recursive=True)
        for filename in files_in_dir:
            filetime = datetime.fromtimestamp(os.path.getmtime(filename))
            if (filetime > self.start_date) and (filetime <= self.end_date):
                incoming_files.append(filename)
        base_files = [os.path.basename(fname) for fname in incoming_files]
        self.logger.info(
            f"Found {len(files_in_dir)} files in incoming directory and {len(base_files)} recent files."
        )
        return (incoming_files, base_files)

    def _create_filelist(self, new_file_list):
        infiles, inbases = self._list_incoming_files()
        oldfiles = self._list_transferred_files()  # Now a set for O(1) lookups
        # Filter out already-transferred files using set membership (O(n) instead of O(n*m))
        new_file_list.extend(
            [filename for filebase, filename in zip(inbases, infiles) if filebase not in oldfiles]
        )
        self.logger.info(
            f"Found {len(infiles)} incoming files, {len(oldfiles)} transferred files, and {len(new_file_list)} new files."
        )
        if self.files_to_append:
            self.files_to_append = (
                self.files_to_append
                if isinstance(self.files_to_append, list)
                else [self.files_to_append]
            )
            new_file_list.extend(self.files_to_append)
            if len(new_file_list) > 0:
                new_file_list = [str(file) for file in new_file_list]
        return new_file_list

    def run(self):
        try:
            new_file_list = []
            self._set_times()
            self._check_dirs()
            new_file_list = self._create_filelist(new_file_list)
            self.logger.info(f"New files: {new_file_list}")
            if self.outfile:
                with open(self.outfile, "w") as outfile:
                    outfile.write("\n".join(new_file_list))
            if (len(new_file_list) > self.maxfiles) and (not self.override_max_files):
                self.logger.error(f"Too many files: list is {len(new_file_list)} elements long")
                raise Exception
            else:
                return {"source": new_file_list}
        except Exception as exc:
            self.logger.error(f"Could not calculate list of new files: {exc}")
            return {"source": []}


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure logging for the newfiles CLI."""
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
        return datetime.now()

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
    """Main CLI entry point for moana-newfiles."""
    parser = argparse.ArgumentParser(
        description="Identify new Moana/Mangōpare sensor files for processing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input directories
    parser.add_argument(
        "--newfile-dir",
        type=Path,
        required=True,
        help="Directory containing new incoming files (e.g., /data_exchange/zebratech/incoming)",
    )
    parser.add_argument(
        "--old-files-dirs",
        nargs="+",
        type=Path,
        required=True,
        help="Directory or directories with already processed files",
    )
    parser.add_argument(
        "--files-to-append",
        nargs="+",
        help="Additional specific files to include in the list",
    )

    # Search parameters
    parser.add_argument(
        "--cutoff",
        type=int,
        default=7,
        help="Days backward from end_date to search for files",
    )
    parser.add_argument(
        "--file-format",
        default="*.csv",
        help="Glob pattern for file matching (e.g., '*.csv', 'MOANA_*.csv')",
    )
    parser.add_argument(
        "--maxfiles",
        type=int,
        default=500,
        help="Maximum number of files to process",
    )
    parser.add_argument(
        "--override-max-files",
        action="store_true",
        help="Allow exceeding maxfiles limit",
    )

    # Output
    parser.add_argument(
        "--outfile",
        type=Path,
        help="Output file path for newfiles list (supports strftime formatting)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write list of new files to JSON format",
    )

    # Cycle time (from Cylc)
    parser.add_argument(
        "--cycle",
        help="Cycle datetime (ISO format or YYYYMMDDTHHMM from Cylc)",
    )
    parser.add_argument(
        "--end-date",
        help="End date for file search (if not specified, uses cycle time or current time)",
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML configuration file with newfiles parameters",
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

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose, args.log_file)

    try:
        # Parse cycle time
        cycle_dt = parse_cycle_time(args.cycle)
        logger.info(f"Cycle time: {cycle_dt}")

        # Parse end_date if provided
        end_date = parse_cycle_time(args.end_date) if args.end_date else cycle_dt

        # Load configuration
        config = {}
        if args.config:
            logger.info(f"Loading configuration from {args.config}")
            with open(args.config) as f:
                config = yaml.safe_load(f) or {}

        # Command-line args override config file
        newfiles_kwargs = {
            "newfile_dir": str(args.newfile_dir) or config.get("newfile_dir"),
            "old_files_dirs": [str(p) for p in args.old_files_dirs]
            if args.old_files_dirs
            else config.get("old_files_dirs", []),
            "files_to_append": args.files_to_append or config.get("files_to_append"),
            "cutoff": args.cutoff or config.get("cutoff", 7),
            "file_format": args.file_format or config.get("file_format", "*.csv"),
            "outfile": str(args.outfile) if args.outfile else config.get("outfile"),
            "end_date": end_date,
            "maxfiles": args.maxfiles or config.get("maxfiles", 500),
            "override_max_files": args.override_max_files
            or config.get("override_max_files", False),
            "logger": logger,
        }

        # Validate required parameters
        if not newfiles_kwargs.get("newfile_dir"):
            logger.error("No newfile_dir specified. Use --newfile-dir")
            return 1
        if not newfiles_kwargs.get("old_files_dirs"):
            logger.error("No old_files_dirs specified. Use --old-files-dirs")
            return 1

        logger.info(f"Searching for new files in {newfiles_kwargs['newfile_dir']}")
        logger.info(f"Comparing against {len(newfiles_kwargs['old_files_dirs'])} old file directories")

        # Create instance and run
        lister = ListIncomingFiles(**newfiles_kwargs)
        lister.set_cycle(cycle_dt)

        result = lister.run()
        new_files = result.get("source", [])

        # Output results
        if new_files:
            logger.info(f"Found {len(new_files)} new files")

            # Optionally write to JSON
            if args.output_json:
                output_data = {
                    "cycle_dt": cycle_dt.strftime("%Y%m%d_%H%Mz"),
                    "total_files": len(new_files),
                    "filelist": new_files,
                }
                args.output_json.parent.mkdir(parents=True, exist_ok=True)
                with open(args.output_json, "w") as f:
                    json.dump(output_data, f, indent=2)
                logger.info(f"Wrote new files list to {args.output_json}")

            # Also write to text file if specified
            if args.outfile:
                outfile_path = cycle_dt.strftime(str(args.outfile))
                Path(outfile_path).parent.mkdir(parents=True, exist_ok=True)
                with open(outfile_path, "w") as f:
                    f.write("\n".join(new_files))
                logger.info(f"Wrote new files list to {outfile_path}")

            return 0
        else:
            logger.info("No new files found")
            return 0

    except Exception as e:
        logger.exception(f"Newfiles identification failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
