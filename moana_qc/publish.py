"""Publication module for THREDDS data formatting."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import yaml

from moana_qc.utils import load_yaml

xr.set_options(keep_attrs=True)


class Wrapper:
    """
    Wrapper class for publication of observational data onto THREDDS servers.
    Takes a list of quality-controlled netcdf files and reformats the ones available
    for public access using CF-1.6 conventions and following IMOS and ARGOS conventions
    IMOS: https://s3-ap-southeast-2.amazonaws.com/content.aodn.org.au/Documents/IMOS/Conventions/IMOS_NetCDF_Conventions.pdf
    ARGOS: https://archimer.ifremer.fr/doc/00187/29825/94819.pdf

    Arguments:
        filelist -- list of files to apply transformation to
        outfile_ext -- extension to add to filenames when saving as netcdf files
        out_dir - directory to save public netcdf files (to send to THREDDS server)
        qc_class -- python class wrapper for running qc tests, returns updated xarray dataset
            that includes qc flags and updated status_file
        attr_file -- location of attribute_list.yml, default uses the one in the python
            package, should be a yaml file (see sample one in ops_qc directory)

    Returns:
        self._success_files -- list of files successfully reformatted and saved as new netcdf files

    Outputs:
        Saves public files as netcdf in out_dir
    """

    def __init__(
        self,
        filelist=None,
        filelist_json=None,
        outfile_ext="published",
        out_dir=None,
        status_file_dir=None,
        attr_file=os.path.join(os.path.dirname(os.path.realpath(__file__)), "attribute_list.yml"),
        var_attr_dict_name="vars_attr_info",
        global_attr_dict_name="global_attr_info",
        coords_attr_dict_name="coords_attr_info",
        global_attrs_dict="global_attrs",
        logger=logging,
        **kwargs,
    ):
        # Extract filelist from config if passed via kwargs (from linked parent tasks)
        if filelist is None and "config" in kwargs:
            filelist = kwargs["config"].get("filelist")
            if filelist:
                print(f"Extracted filelist from config kwargs: {len(filelist)} files")

        self.filelist = filelist
        self.filelist_json = filelist_json
        self.status_file_dir = status_file_dir
        self.outfile_ext = outfile_ext
        self.out_dir = out_dir
        self.attr_file = attr_file
        self.var_attr_dict_name = var_attr_dict_name
        self.global_attr_dict_name = global_attr_dict_name
        self.coords_attr_dict_name = coords_attr_dict_name
        self.global_attrs_dict = global_attrs_dict
        self.logger = logging
        self.coords_info = load_yaml(self.attr_file, self.coords_attr_dict_name)
        self.vars_info = load_yaml(self.attr_file, self.var_attr_dict_name)
        self.global_attr_info = load_yaml(self.attr_file, self.global_attr_dict_name)
        self.global_attrs = load_yaml(self.attr_file, self.global_attrs_dict)
        self.time_varname_source = next(
            var for var, varinfo in self.coords_info.items() if "TIME" in var
        )
        self.time_varname_destination = next(
            varinfo["new_name"] for var, varinfo in self.coords_info.items() if "TIME" in var
        )
        self._saved_files = {"filelist": []}

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt

    def _available_for_publication(self, filename):
        try:
            # Open dataset once for efficiency
            ds = xr.open_dataset(filename, cache=False, engine="netcdf4")
            
            # Check if data is public
            public = ds.attrs["public"]
            
            # Convert public attribute to boolean (handles TRUE/True/true strings)
            if isinstance(public, str):
                is_public = public.upper() == "TRUE"
            elif isinstance(public, bool):
                is_public = public
            else:
                is_public = bool(public)
            
            if not is_public:
                self.logger.debug(f"File {filename} is not marked as public")
                return False
            
            # Check if the current data is after the agreement signature date
            self.first_measurement = ds[self.time_varname_source][0].values
            self.last_measurement = ds[self.time_varname_source][-1].values
            
            publication_date_str = ds.attrs["publication_date"]
            
            # Handle FALSE or invalid publication dates
            if publication_date_str == "FALSE" or not publication_date_str:
                self.logger.debug(f"File {filename} has invalid publication_date: {publication_date_str}")
                return False
            
            publication_date = datetime.strptime(publication_date_str, "%d/%m/%Y")
            publication_date = np.datetime64(publication_date)
            
            if self.first_measurement >= publication_date:
                self.logger.info(f"File {filename} is available for publication")
                return True
            else:
                self.logger.debug(
                    f"File {filename} first measurement ({self.first_measurement}) "
                    f"is before publication date ({publication_date})"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking publication status for {filename}: {e}")
            return False

    def _add_global_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.global_attrs.items():
            ## New attributes provided
            if var in self.global_attr_info:
                if "quality_control_log" in var:
                    self.ds.attrs[var] = (
                        self.global_attr_info[var][0]
                        + ": "
                        + self.ds_o.attrs[self.global_attr_info[var][0]][1:-1].replace("'", "")
                        + "; "
                        + self.global_attr_info[var][1]
                        + ": "
                        + self.ds_o.attrs[self.global_attr_info[var][1]]
                    )
                elif "instrument" in var:
                    max_depth = self.ds_o.attrs["max_lifetime_depth"].split()[0]
                    if float(max_depth) > 200:
                        self.ds.attrs[var] = self.global_attr_info[var].format(1000)
                    else:
                        self.ds.attrs[var] = self.global_attr_info[var].format(200)
                else:
                    self.ds.attrs[var] = self.global_attr_info[var]
            else:
                try:
                    self.ds.attrs[var] = self.ds_o.attrs[varinfo]
                except:
                    if "vertical_max" in var:
                        self.ds.attrs[var] = str(np.round(self.ds["DEPTH"].max().values, 1))
                    elif "vertical_min" in var:
                        self.ds.attrs[var] = str(np.round(self.ds["DEPTH"].min().values, 1))
                    elif "time_coverage_start" in var:
                        self.ds.attrs[var] = pd.to_datetime(self.first_measurement).strftime(
                            "%d/%m/%Y %H:%M:%S"
                        )
                    elif "time_coverage_end" in var:
                        self.ds.attrs[var] = pd.to_datetime(self.last_measurement).strftime(
                            "%d/%m/%Y %H:%M:%S"
                        )
                    else:
                        self.ds.attrs[var] = ""
                        self.logger.error(f"Could not find value for attribute: {var}")
                        pass
        self.ds.attrs["publication_date"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    def _add_var_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.vars_info.items():
            if "new_name" in varinfo:
                var = varinfo["new_name"]
            for attr, attrinfo in varinfo.items():
                if "new_name" not in attr:
                    self.ds[var].attrs[attr] = attrinfo

    def _add_coords_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.coords_info.items():
            if "new_name" in varinfo:
                var = varinfo["new_name"]

            for attr, attrinfo in varinfo.items():
                if "new_name" not in attr:
                    self.ds[var].attrs[attr] = attrinfo

                if "TIME" in var and "unit" in attr:
                    self.ds[var].attrs[attr] = self.ds_o[self.time_varname_source].attrs[attr]

    def _reformat_file(self):
        self.ds_o = xr.open_dataset(self.filename, cache=False, decode_cf=False)
        ### Generate new file using the data from the previous file
        df = pd.DataFrame()
        for coords, items in self.coords_info.items():
            if "new_name" in items:
                coordsn = items["new_name"]
                df[coordsn] = self.ds_o[coords]
            else:
                df[coords] = self.ds_o[coords]

        for var, items in self.vars_info.items():
            if "new_name" in items:
                varn = items["new_name"]
                df[varn] = self.ds_o[var]
            else:
                df[var] = self.ds_o[var]
        df = df.set_index([self.time_varname_destination])
        self.ds = xr.Dataset.from_dataframe(df)
        for coords, items in self.coords_info.items():
            if "new_name" in items:
                coords = items["new_name"]
            self.ds = self.ds.assign_coords({coords: self.ds[coords]})
        ## Adding attributes
        self._add_coords_attrs()
        self._add_var_attrs()
        self._add_global_attrs()

    def _initialize_outdir(self, dir_path):
        """
        Check if outdir exists, create if not
        """
        try:
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
        except Exception as exc:
            self.logger.error(
                f"Could not create specified directory to save publishable files in: {exc}"
            )

    def _save_success_files_list(self):
        """
        Save list of successfully published files to a JSON file.
        Includes metadata like timestamp and file count for validation.
        If status_file_dir is not specified, saves in same directory as published data.
        Saves to a 'filelist' subdirectory.
        Filename uses cycle_dt in format: published_files_list_YYYYMMDD_HHMMz.json
        """
        # Skip if no files were successfully saved
        if not self._saved_files["filelist"]:
            self.logger.info("No published files to save to JSON list")
            return

        try:
            if not self.status_file_dir:
                self.status_file_dir = self.out_dir

            if not self.status_file_dir:
                self.logger.warning(
                    "Cannot save published files list: no output directory specified"
                )
                return

            # Create filelist subdirectory
            filelist_dir = os.path.join(self.status_file_dir, "filelist")
            self._initialize_outdir(filelist_dir)

            # Format filename with cycle_dt as YYYYMMDD_HHMMz
            basefile = self.cycle_dt.strftime("published_files_list_%Y%m%d_%H00z.json")
            filename = os.path.join(filelist_dir, basefile)

            # Prepare JSON structure with metadata
            published_data = {
                "cycle_dt": self.cycle_dt.strftime("%Y%m%d_%H%Mz"),
                "total_files": len(self._saved_files["filelist"]),
                "published_files": self._saved_files["filelist"],
            }

            # Write JSON file
            with open(filename, "w") as f:
                json.dump(published_data, f, indent=2)

            msg = (
                f"Saved list of {len(self._saved_files['filelist'])} published files to {filename}"
            )
            self.logger.info(msg)
            print(msg)  # Ensure visibility in scheduler logs
        except Exception as exc:
            error_msg = f"Could not save published files list: {exc}"
            self.logger.error(error_msg)
            print(f"ERROR: {error_msg}")  # Ensure visibility in scheduler logs
            import traceback

            traceback.print_exc()  # Print full traceback for debugging

    def _set_filelist(self):
        if hasattr(self, "_success_files") and not self.filelist:
            self.filelist = self._success_files

        # Read from JSON file if filelist still not set
        if not self.filelist and self.filelist_json:
            # Format the path with cycle_dt if available
            filelist_json_path = (
                self.cycle_dt.strftime(self.filelist_json)
                if hasattr(self, "cycle_dt")
                else self.filelist_json
            )
            try:
                with open(filelist_json_path) as f:
                    data = json.load(f)
                # Support 'filelist', 'published_files', and 'success_files' keys
                self.filelist = data.get("filelist", [])
                self.logger.info(f"Loaded {len(self.filelist)} files from {filelist_json_path}")
            except Exception as e:
                self.logger.error(f"Could not read filelist JSON {filelist_json_path}: {e}")

        if not self.filelist:
            self.logger.error(
                "No file list found, please specify.  No transformation for publication performed."
            )

    def run(self):
        # self.set_cycle()
        self._set_filelist()
        for file in self.filelist:
            if self._available_for_publication(file):
                self.filename = file
                self._reformat_file()
                head, tail = os.path.split(self.filename)
                if not self.out_dir:
                    self.out_dir = head
                # create (mkdir) out_dir if it doesn't exist
                self._initialize_outdir(self.out_dir)
                name = os.path.splitext(tail)[0].split("_")
                end_date_name = pd.to_datetime(self.last_measurement).strftime("%Y%m%d_%H%M%S")
                savefile = os.path.join(
                    self.out_dir,
                    f"{name[0]}_{end_date_name}{self.outfile_ext}.nc"
                )
                
                # Fix QC variables: convert int8 with incompatible _FillValue to int32
                # or remove _FillValue if not needed
                for var in list(self.ds.data_vars) + list(self.ds.coords):
                    if self.ds[var].dtype == np.int8:
                        fill_value = self.ds[var].attrs.get("_FillValue")
                        if fill_value is not None:
                            try:
                                # Try to convert fill_value to int8
                                np.int8(fill_value)
                            except (ValueError, OverflowError):
                                # Fill value doesn't fit in int8, convert variable to int32
                                self.logger.debug(
                                    f"Variable {var}: converting from int8 to int32 due to _FillValue={fill_value}"
                                )
                                self.ds[var] = self.ds[var].astype(np.int32)
                                self.ds[var].attrs["_FillValue"] = np.int32(fill_value)
                
                # Fix SerializationWarning: remove 'coordinates' attributes from variables
                # to let xarray handle coordinate encoding automatically
                for var in self.ds.data_vars:
                    if "coordinates" in self.ds[var].attrs:
                        del self.ds[var].attrs["coordinates"]
                
                # Remove global 'coordinates' attribute if it exists
                if "coordinates" in self.ds.attrs:
                    del self.ds.attrs["coordinates"]
                
                # Save without explicit encoding
                self.ds.to_netcdf(savefile, mode="w", format="NETCDF4")
                self._saved_files["filelist"].append(savefile)

        # Save the list of published files to JSON

        self._save_success_files_list()

        return self._saved_files


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure logging for the publish CLI."""
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
    """Main CLI entry point for moana-publish."""
    parser = argparse.ArgumentParser(
        description="Publish Moana/Mangōpare QC'd data to THREDDS-compatible format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/Output
    parser.add_argument(
        "--filelist", 
        nargs="+", 
        help="List of QC'd NetCDF files to publish"
    )
    parser.add_argument(
        "--filelist-json",
        type=Path,
        help="JSON file containing list of files to publish (e.g., from moana-qc output)",
    )
    parser.add_argument(
        "--config", 
        type=Path, 
        help="YAML configuration file with publishing parameters"
    )
    parser.add_argument(
        "--out-dir", 
        type=Path, 
        help="Output directory for published NetCDF files"
    )
    parser.add_argument(
        "--status-file-dir", 
        type=Path, 
        help="Directory for status files and filelist outputs"
    )

    # Cycle time (from Cylc)
    parser.add_argument(
        "--cycle", 
        help="Cycle datetime (ISO format or YYYYMMDDTHHMM from Cylc)"
    )

    # Publication parameters
    parser.add_argument(
        "--outfile-ext",
        default="_published",
        help="Extension to add to published filenames",
    )
    parser.add_argument(
        "--attr-file", 
        type=Path, 
        help="YAML file with publication attributes"
    )

    # Logging
    parser.add_argument(
        "-v", 
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--log-file", 
        type=Path, 
        help="Write logs to file"
    )

    # Output
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write list of published files to JSON",
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
            "out_dir": str(args.out_dir) if args.out_dir else config.get("out_dir"),
            "status_file_dir": str(args.status_file_dir)
            if args.status_file_dir
            else config.get("status_file_dir"),
            "outfile_ext": args.outfile_ext or config.get("outfile_ext", "_published"),
            "attr_file": str(args.attr_file) if args.attr_file else config.get("attr_file"),
            "logger": logger,
        }

        # Check we have files to process
        if not wrapper_kwargs.get("filelist") and not wrapper_kwargs.get("filelist_json"):
            logger.error("No files specified. Use --filelist or --filelist-json")
            return 1

        logger.info("Initializing publication wrapper...")

        # Create wrapper and run
        wrapper = Wrapper(**wrapper_kwargs)
        wrapper.set_cycle(cycle_dt)

        saved_files = wrapper.run()

        # Output results
        if saved_files and saved_files.get("filelist"):
            published_list = saved_files["filelist"]
            logger.info(f"Successfully published {len(published_list)} files")

            # Optionally write to JSON
            if args.output_json:
                output_data = {
                    "cycle_dt": cycle_dt.strftime("%Y%m%d_%H%Mz"),
                    "total_files": len(published_list),
                    "published_files": published_list,
                }
                args.output_json.parent.mkdir(parents=True, exist_ok=True)
                with open(args.output_json, "w") as f:
                    json.dump(output_data, f, indent=2)
                logger.info(f"Wrote published list to {args.output_json}")

            return 0
        else:
            logger.warning("No files were published")
            return 1

    except Exception as e:
        logger.exception(f"Publication failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
