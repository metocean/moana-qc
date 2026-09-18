"""Quality control wrapper for Moana/Mangōpare sensor data."""

from __future__ import annotations

import glob
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import gsw
import numpy as np
import pandas as pd
import xarray as xr

from moana_qc.utils import catch, import_pycallable, start_end_dist

xr.set_options(keep_attrs=True)

# Load gear classifications from config file
_GEAR_CLASS_FILE = Path(__file__).parent / "gear_classifications.yml"

def _load_gear_classifications() -> dict:
    """Load gear classifications from YAML config file."""
    try:
        import yaml
        with open(_GEAR_CLASS_FILE) as f:
            config = yaml.safe_load(f)
        return config.get("GEAR_CLASSIFICATIONS", {})
    except Exception:
        # Fallback to empty dict if file doesn't exist
        return {}

DEFAULT_GEAR_CLASS = _load_gear_classifications()

class QcWrapper:
    """Quality control wrapper for observational data.
    Processes CSV files containing Moana/Mangōpare data and outputs QC'd netCDF files.
    Creates a status file indicating success/failure for each file.
    Designed for use in Cylc workflows where cycle_dt is managed by the workflow.

    Arguments:
        filelist -- list of csv files to apply quality control to
        outfile_ext -- extension to add to filenames when saving as netcdf files
        out_dir - directory to save qc'd netcdf files in
        test_list_1 -- list of qc tests to run in the first "batch," these tests should not
            depend on a previous test
        test_list_2 -- list of qc tests to run in the second "batch," which may depend on 
            qc tests in test_list_1
        fishing_metafile -- path and filename for the csv file that contains fisher metadata,
            can be a local directory or a csv file in a github repository
        metafile_username -- used if you need a username to access metafile on github
        metafile_token -- github token if you need a username to access metafile on github
        status_file_ext -- extension added to status_file_XXXXXX.csv, usually a datetime
        status_file_dir -- directory to save status file in, if empty, will use out_dir
        datareader -- python class to read csv file, returns an xarray dataset
        preprocessor -- python class to preprocess data from datareader, returns updated
            xarray dataset and updated status_file
        qc_class -- python class wrapper for running qc tests, returns updated xarray dataset
            that includes qc flags and updated status_file
        save_flags -- boolean, save all qc flags (true) or only global qc flags (false)
        convert_p_to_z -- boolean, convert pressure to depth (true) or only keep pressure
            (false)
        default_latitude -- latitude to use in convert_p_to_z
        attr_file -- location of attribute_list.yml, default uses the one in the python 
            package
        startstring -- string, used by datareader class to recognize the end of the header
            or start of the data
        splitstring -- string, string to look for in error messages, anything before 
            splitstring will be recorded in status_file_XXXX as "failure_mode", anything
            after as "detailed_error"
        gear_class -- dictionary of fishing_method:gear_class pairs, matching every 
            fishing method in the fishing_metafile to either "mobile" or "stationary"

    Returns:
        self._success_files -- list of files successfully qc'd and saved as netcdf files

    Outputs:
        Saves qc'd files as netcdf in out_dir
        Saves status_file_XXXX as csv in status_file_dir (or if none, out_dir)
    """

    def __init__(
        self,
        filelist: list[str] | None = None,
        outfile_ext: str = "_qc",
        out_dir: str | None = None,
        test_list_1: list[str] | None = None,
        test_list_2: list[str] | None = None,
        fishing_metafile: str = "/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv",
        metafile_username: str | None = None,
        metafile_token: str | None = None,
        status_file_ext: str = "_%y%m%d",
        status_file_dir: str = "",
        datareader: dict | None = None,
        metareader: dict | None = None,
        preprocessor: dict | None = None,
        qc_class: dict | None = None,
        save_flags: bool = False,
        convert_p_to_z: bool = True,
        default_latitude: float = -40.0,
        attr_file: str | Path | None = None,
        startstring: str = "DateTime (UTC)",
        splitstring: str = "due to:",
        gear_class: dict | None = None,
        logger: logging.Logger = logging.getLogger(__name__),
        **kwargs,
    ):
        # Extract filelist from config if passed via kwargs (from linked parent tasks)
        if filelist is None and 'config' in kwargs:
            filelist = kwargs['config'].get('filelist')
            if filelist:
                logger.info(f"Extracted filelist from config kwargs: {len(filelist)} files")

        # Expand glob patterns in filelist
        if filelist:
            expanded_filelist = []
            for pattern in filelist:
                # Check if pattern contains glob wildcard characters
                if any(char in pattern for char in ['*', '?', '[']):
                    matches = sorted(glob.glob(pattern))
                    if matches:
                        expanded_filelist.extend(matches)
                        logger.info(f"Expanded glob pattern '{pattern}' to {len(matches)} files")
                    else:
                        logger.warning(f"Glob pattern '{pattern}' matched no files")
                else:
                    # Not a glob pattern, add as-is
                    expanded_filelist.append(pattern)
            filelist = expanded_filelist if expanded_filelist else filelist

        self.filelist = filelist
        self.outfile_ext = outfile_ext
        self.out_dir = out_dir
        self.test_list_1 = test_list_1 or []
        self.test_list_2 = test_list_2 or []
        self.metafile = fishing_metafile
        self.metafile_username = metafile_username
        self.metafile_token = metafile_token
        self.status_file_ext = status_file_ext
        self.status_file_dir = status_file_dir
        self.datareader_class = datareader or {}
        self.metareader_class = metareader or {}
        self.preprocessor_class = preprocessor or {}
        self.qc_class = qc_class or {}
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.default_latitude = default_latitude
        # Use default attr_file if not provided
        self.attr_file = Path(attr_file) if attr_file else Path(__file__).parent / "attribute_list.yml"
        self.startstring = startstring
        self.splitstring = splitstring
        # Use provided gear_class or load from config file
        self.gear_class = gear_class or DEFAULT_GEAR_CLASS
        # Default class names (updated for moana_qc package)
        self._default_datareader_class = "moana_qc.readers.MangopareStandardReader"
        self._default_metareader_class = "moana_qc.readers.MangopareMetadataReader"
        self._default_preprocessor_class = "moana_qc.preprocess.PreProcessMangopare"
        self._default_qc_class = "moana_qc.apply_qc.QcApply"
        self.logger = logger
        self.status_dict_keys = [
            "filename",
            "baseline",
            "cellular_signal_strength",
            "date_quality_controlled",
            "deck_unit_battery_percent",
            "deck_unit_battery_voltage",
            "download_time",
            "gear_class",
            "max_lifetime_depth",
            "moana_battery",
            "moana_serial_number",
            "moana_calibration_date",
            "qc=1",
            "qc=2",
            "qc=3",
            "qc=4",
            "reset_codes",
            "reset_codes_data",
            "saved",
            "failed",
            "failure_mode",
            "total_obs",
            "detailed_error"
        ]

    def set_cycle(self, cycle_dt: datetime) -> None:
        """Set the cycle datetime (typically from Cylc workflow)."""
        self.cycle_dt = cycle_dt
        if self.out_dir:
            self.out_dir = cycle_dt.strftime(self.out_dir)
        if self.outfile_ext:
            self.outfile_ext = cycle_dt.strftime(self.outfile_ext)

    def _set_class(self, in_class, default_class):
        klass = in_class.pop("class", default_class)
        out_class = import_pycallable(klass)
        self.logger.info(f"Using class: {klass}")
        return out_class

    def _set_all_classes(self):
        try:
            self.datareader = self._set_class(
                self.datareader_class, self._default_datareader_class
            )
            self.metareader = self._set_class(
                self.metareader_class, self._default_metareader_class
            )
            self.preprocessor = self._set_class(
                self.preprocessor_class, self._default_preprocessor_class
            )
            self.qc_class = self._set_class(
                self.qc_class, self._default_qc_class
            )
        except Exception as exc:
            self.logger.error(f"Unable to set required classes for qc: {exc}")
            raise type(exc)(f"Unable to set requred classes for qc due to: {exc}") from exc


    def _set_filelist(self):
        try:
            if hasattr(self, "_success_files"):
                self.files_to_qc = self._success_files
            else:
                self.files_to_qc = self.filelist
        except Exception as exc:
            self.logger.error(
                "No file list found, please specify.  No QC performed.")
            raise type(exc)(f'No file list found, no QC performed due to: {exc}') from exc


    def _save_qc_data(self, filename):
        """
        Save qc'd data as netcdf files.  If no outdir specified,
        saves in same directory as original file.
        """
        try:
            head, tail = os.path.split(filename)
            if not self.out_dir:
                self.out_dir = head
            # create (mkdir) out_dir if it doesn't exist
            self._initialize_outdir(self.out_dir)
            savefile = os.path.join(
                self.out_dir, "{}{}{}".format(
                    os.path.splitext(tail)[0], self.outfile_ext, ".nc")
            )
            self.ds.to_netcdf(savefile, mode="w", format="NETCDF4")
            # self._saved_files.append(savefile)
            self.status_dict.update({"saved": "yes"})
            self._saved_files.append(savefile)
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Save QC File Failed"}
            )
            self.logger.error(f"Could not save qc data from {filename}: {exc}")
            # self._failed_files.append(f'{filename}: Save QC File Failed')

    def _save_status_data(self):
        """
        Save self._success_files and self._failed_files as text files.
        If status_file_dir is not specified, saves in same directory as
        qc'd data.
        """
        try:
            if not self.status_file_dir:
                self.status_file_dir = self.out_dir
            # create (mkdir) status_file_dir if it doesn't exist
            self._initialize_outdir(self.status_file_dir)
            # create all the status files in self.save_file_dict
            #           for name,data in save_file_dict:
            basefile = f"status_file{self.status_file_ext}.csv"
            filename = self.cycle_dt.strftime(
                os.path.join(self.status_file_dir, basefile))
            self._status_data.to_csv(
                filename, mode="a", header=not os.path.isfile(filename), index=False
            )
        except Exception as exc:
            self.logger.error(f"Could not save status files: {exc}")

    def _save_success_files_list(self):
        """
        Save list of successfully processed files to a JSON file.
        Includes metadata like timestamp and file count for validation.
        If status_file_dir is not specified, saves in same directory as qc'd data.
        Saves to a 'filelist' subdirectory.
        Filename uses cycle_dt in format: success_files_list_YYYYMMDD_HHMMz.json
        """
        # Skip if no files were successfully saved
        if not self._saved_files:
            self.logger.info("No successful files to save to JSON list")
            return
        try:
            if not self.status_file_dir:
                self.status_file_dir = self.out_dir

            if not self.status_file_dir:
                self.logger.warning("Cannot save success files list: no output directory specified")
                return

            # Create filelist subdirectory
            filelist_dir = os.path.join(self.status_file_dir, 'filelist')
            self._initialize_outdir(filelist_dir)

            # Format filename with cycle_dt as YYYYMMDD_HHMMz
            basefile = self.cycle_dt.strftime("success_files_list_%Y%m%d_%H00z.json")
            filename = os.path.join(filelist_dir, basefile)

            # Prepare JSON structure with metadata
            success_data = {
                "cycle_dt": self.cycle_dt.strftime("%Y%m%d_%H%Mz"),
                "total_files": len(self._saved_files),
                "filelist": self._saved_files
            }

            # Write JSON file
            with open(filename, 'w') as f:
                json.dump(success_data, f, indent=2)

            msg = f"Saved list of {len(self._saved_files)} successful files to {filename}"
            self.logger.info(msg)
            print(msg)  # Ensure visibility in scheduler logs
        except Exception as exc:
            error_msg = f"Could not save success files list: {exc}"
            self.logger.error(error_msg)
            print(f"ERROR: {error_msg}")  # Ensure visibility in scheduler logs
            import traceback
            traceback.print_exc()  # Print full traceback for debugging

    def _initialize_outdir(self, dir_path):
        """
        Check if outdir exists, create if not
        """
        try:
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
        except Exception as exc:
            self.logger.error(f"Could not create specified directory {dir_path} to save qc files in: {exc}")
            raise type(exc)(f'Could not create specified directory to save qc files in due to: {exc}') from exc


    def convert_pressure_to_depth(self):
        """
        Converts pressure to depth in the ocean either using the
        mean latitude of the observations or using a default_latitude
        """
        try:
            if not np.isnan(np.nanmean(self.ds["LATITUDE"])):
                d_lat = np.nanmean(self.ds["LATITUDE"])
            else:
                d_lat = self.default_latitude
            depth = [
                gsw.z_from_p(catch(lambda: float(z)), d_lat)
                for z in self.ds["PRESSURE"]
            ]
            self.ds["DEPTH"] = xr.Variable(
                dims="DATETIME",
                data=depth,
                attrs={"units": "[m]", "standard_name": "depth"},
            )
            self.ds["DEPTH"] = self.ds["DEPTH"]*-1
            #self.ds = self.ds.drop("PRESSURE")
            self.ds = self.ds.rename({"PRESSURE_QC": "DEPTH_QC"})
            self.ds["PRESSURE_QC"] = self.ds["DEPTH_QC"]
            self.ds["DEPTH_QC"].attrs["long_name"] = "Overall Depth Quality Flag"
            return self.ds
        except Exception as exc:
            self.logger.error(f"Could not convert pressure to depth, leaving as pressure: {exc}")
            pass

    def _calc_positions(self, filename, surface_pressure=10, qcrange=None):
        """
        Calculate locations for either stationary or mobile gear.
        Current state of this code assumes all stationary locations
        in one CSV file are the SAME.  NOT NECESSARILY TRUE!  Hence
        the commented out regions...eventually will use those.
        """
        if qcrange is None:
            qcrange = [1, 2]
        try:
            if self.ds.attrs['gear_class'] == 'stationary':
                # Filter to good quality data points using boolean indexing
                ds2 = self.ds
                if 'LOCATION_QC' in self.ds.data_vars and 'DATETIME_QC' in self.ds.data_vars:
                    good_mask = (
                        (self.ds['LOCATION_QC'].isin(qcrange)) & 
                        (self.ds['DATETIME_QC'].isin(qcrange))
                    )
                    ds2 = self.ds.isel(DATETIME=good_mask)
                elif 'LOCATION_QC' in self.ds.data_vars:
                    good_mask = self.ds['LOCATION_QC'].isin(qcrange)
                    ds2 = self.ds.isel(DATETIME=good_mask)

                if len(ds2.DATETIME) > 0:
                    lat = np.nanmean([ds2.LATITUDE.values[0], ds2.LATITUDE.values[-1]])
                    lon = np.nanmean([ds2.LONGITUDE.values[0], ds2.LONGITUDE.values[-1]]) % 360
                    self.ds['LATITUDE'] = self.ds.LATITUDE.where(lat == self.ds.LATITUDE, other=lat)
                    self.ds['LONGITUDE'] = self.ds.LONGITUDE.where(lon == self.ds.LONGITUDE, other=lon)
            if self.ds.attrs['gear_class'] == 'mobile':
                self.ds = self.ds.assign({"LONGITUDE": lambda ds: ds['LONGITUDE'] % 360})
        except Exception as exc:
            self.logger.error(
                f"Position could not be calculated for {filename}: {exc}")
            raise type(exc)(f'Could not calculate stationary positions (len={len(self.ds.TEMPERATURE)}) due to: {exc}') from exc

    def _calc_location_attrs(self,filename):
        """
        Assigns derived position attributes to netdf and
        calculates the start_end_dist
        """
        try:
            self.ds.attrs['geospatial_lat_max'] = f"{np.nanmax(self.ds.LATITUDE.values):.6f}"
            self.ds.attrs['geospatial_lat_min'] = f"{np.nanmin(self.ds.LATITUDE.values):.6f}"
            self.ds.attrs['geospatial_lon_max'] = f"{np.nanmax(self.ds.LONGITUDE.values):.6f}"
            self.ds.attrs['geospatial_lon_min'] = f"{np.nanmin(self.ds.LONGITUDE.values):.6f}"
            sed = start_end_dist(self.ds)
            self.ds.attrs['start_end_dist_m'] = f"{sed:.2f}"
        except Exception as exc:
            self.logger.error(
                f"Position attrs not assigned for {filename}: {exc}")
            raise type(exc)(f'Position attrs or start_end_dist not assigned due to: {exc}') from exc


    def _postprocess(self, filename):
        """
        If gear class is not unknown, apply QC, convert pressure to depth
        if desired, check if any bad data, save file.
        """
        try:
            # only save files with at least some good data
            if np.nanmin(self.ds["QC_FLAG"]) < 4:
                if self.convert_p_to_z:
                    self.ds = self.convert_pressure_to_depth()
                self._save_qc_data(filename)
                self.status_dict["total_obs"] = len(self.ds["DATETIME"])
                # this is annoying but it didn't want to unpack single tuples...
                values, counts = np.unique(
                    self.ds["QC_FLAG"].values, return_counts=True
                )
                if len(values) > 1:
                    for value, count in zip(values, counts):
                        self.status_dict[f"qc={value}"] = count
                else:
                    self.status_dict[f"qc={values[0]}"] = counts[0]
            else:
                self.status_dict.update(
                    {"failed": "yes",
                        "failure_mode": "No Good Data (all QC Flags = 4)"}
                )
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Post-Processing Failed"})
            self.logger.error(
                f"Could not postprocess {filename} due to {exc}")

    def _qc_files(self, test_list, filename):
        try:
            self.ds = self.qc_class(
                self.ds,
                test_list,
                self.save_flags,
                self.attr_file,
                ).run()
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Apply QC Tests Failed"})
            self.logger.error(
                f"Could not qc {filename} due to {exc}")

    def _update_status(self, filename):
        try:
            status_dict2 = {
                k: self.status_dict[k]
                for k in self.status_dict_keys
                if k in self.status_dict
            }
            status_dict2['filename'] = filename
            #self._status_data = self._status_data.append(
            #    status_dict2, ignore_index=True)
            self._status_data = pd.concat([self._status_data, pd.DataFrame([status_dict2])], ignore_index=True)
        except Exception as exc:
            self.logger.error(f"Could not append status info for {filename} due to {exc}")

    def _status_checks(self, filename):
        check_passed = True
        if not hasattr(self.ds, "expected_deck_unit_serial_number"):
            if "failed" not in self.status_dict:
                self.status_dict.update(
                    {
                        "failed": "yes",
                        "failure_mode": "Expected deck unit unknown.",
                    }
                )
            self._update_status(filename)
            check_passed = False
        elif int(self.ds.attrs["deck_unit_serial_number"]) != int(
            self.ds.attrs["expected_deck_unit_serial_number"]
        ):
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Deck units do not match!"}
            )
            self._update_status(filename)
            check_passed = False
        elif self.ds.attrs["gear_class"] == "unknown":
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Gear Class Unknown"}
            )
            self._update_status(filename)
            check_passed = False
        return check_passed

    def _process_files(self):
        """Read, reprocess, and apply qc"""
        self._status_data = pd.DataFrame(columns=self.status_dict_keys)
        self._saved_files = []
        self._set_filelist()

        # apply qc
        for filename in self.files_to_qc:
            self.status_dict = {}
            try:
                self.ds = self.datareader(filename=filename).run()
                self.ds, self.status_dict = self.preprocessor(
                    ds=self.ds,
                    fisher_metadata=self.fisher_metadata,
                    attr_file=self.attr_file,
                    status_dict=self.status_dict
                ).run()
                passed = self._status_checks(filename)
                if not passed:
                    continue
                self._qc_files(self.test_list_1,filename)
                self._calc_location_attrs(filename)
                self._calc_positions(filename)
                if self.ds.attrs['gear_class'] == 'stationary':
                    self._qc_files(self.test_list_2,filename)
                self._postprocess(filename)
                self._update_status(filename)
            except Exception as exc:
                if self.splitstring in str(exc):
                    estr = str(exc).split(self.splitstring)
                    self.status_dict.update({"failed": "yes","failure_mode":estr[0],"detailed_error":estr[1]})
                else:
                    self.status_dict.update({"failed": "yes","failure_mode":str(exc),"detailed_error":"NA"})
                self._update_status(filename)
                self.logger.error(
                    f"Could not qc data from {filename}. Traceback: {exc}"
                )
        self._save_status_data()
        self._save_success_files_list()
        self._success_files = self._saved_files

    def run(self):
        """Run the QC processing workflow.
        Returns:
            list: List of successfully processed files, or None if no files
        """
        # set all readers/preprocessors
        if not hasattr(self, 'cycle_dt'):
            # If no cycle set, use current time (for non-Cylc usage)
            self.set_cycle(datetime.now())
        self._set_all_classes()
        # load metadata common for all files
        self.fisher_metadata = self.metareader(
            metafile=self.metafile,
            gear_class=self.gear_class,
            username=self.metafile_username,
            token=self.metafile_token,
        ).run()
        if len(self.filelist) < 1 or not self.filelist:
            self.logger.info(
                'No files in filelist, exiting without performing qc and returning "None".'
            )
            self._success_files = None
        else:
            self._process_files()
        return self._success_files
