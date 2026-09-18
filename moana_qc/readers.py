"""Data readers for Moana/Mangōpare sensor files."""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import moana_qc
from moana_qc.utils import catch


class MangopareStandardReader:
    """Read Mangopare temperature and pressure sensor data.

    Loads Mangopare CSV data into pandas DataFrame, then converts to xarray Dataset.
    Standardizes column names and formats for quality control processing.

    Args:
        filename: Path to Mangopare CSV file
        filetype: Type of file ('sensor' or 'fisherdata')
        dateformat: Date format string for parsing timestamps
        startstring: First column name (used to skip header)
        skip_rows: Number of header rows to skip
        default_reset_value: Default value used to identify reset events
        logger: Logger instance

    Attributes:
        ds: xarray Dataset containing sensor data and attributes
    """

    def __init__(
        self,
        filename: str | Path,
        filetype: str = "sensor",
        dateformat: str = "%Y%m%dT%H%M%S",
        startstring: str = "DateTime (UTC)",
        skip_rows: int = 11,
        default_reset_value: float = 44.444,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.filename = str(filename)
        self.filetype = filetype
        self.dateformat = dateformat
        self.startstring = startstring
        self.skip_rows = skip_rows
        self.default_reset_value = default_reset_value
        self.logger = logger

        self.global_attrs = {
            "date_quality_controlled": datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%dT%H:%M:%S %z"),
            "quality_control_repository": "https://github.com/metocean/moana-qc",
            "qc_package_version": moana_qc.__version__,
            "raw_data_filename": self.filename,
        }

    def _read_mangopare_csv(self):
        """
        Opens a mangopare csv file in pandas, formats the data, converts to xarray
        """
        try:
            self.start_line = self._calc_header_rows(default_skiprows=self.skip_rows)
            self.df = pd.read_csv(
                self.filename,
                skiprows=self.start_line,
                on_bad_lines="error",
                float_precision="round_trip",
            )
        except Exception as exc:
            self.logger.error(f"Could not read csv file {self.filename} due to {exc}")
            raise type(exc)(f"Could not read csv file due to: {exc}") from exc

    def _format_df_data(self):
        """
        Miscellaneous Mangopare data formatting
        If there is more than one observation at the same time,
        only keeps first one.
        """
        try:
            depth_col = [col for col in self.df.columns if ("Depth") in col]
            if len(depth_col) == 1:
                self.df.rename(
                    columns={
                        str(depth_col[0]): "PRESSURE",
                        "DateTime (UTC)": "DATETIME",
                        "Lat": "LATITUDE",
                        "Lon": "LONGITUDE",
                        "Temperature C": "TEMPERATURE",
                    },
                    inplace=True,
                )
            else:
                self.logger.error(f"Column name not recognized in {self.filename}")
            self.df["DATETIME"] = pd.to_datetime(
                self.df["DATETIME"], format=self.dateformat, errors="coerce"
            )
            # if duplicate datetimes, only keep first
            self.df = self.df.drop_duplicates(subset=["DATETIME"], keep="first")
            self.df["TEMPERATURE"] = [catch(lambda t=t: float(t)) for t in self.df["TEMPERATURE"]]
            # Convert 0 lat/lon to nan, since 0 is bad value, but don't drop
            self.df["LONGITUDE"] = self.df["LONGITUDE"].replace(0, np.nan)
            self.df["LATITUDE"] = self.df["LATITUDE"].replace(0, np.nan)

        except Exception as exc:
            self.logger.error(f"Formatting of data failed for {self.filename}: {exc}")
            raise type(exc)(f"Could not format dataframe due to: {exc}") from exc

    def _convert_df_to_ds(self):
        """
        Sets dims and coords, converts to xaxrray dataset.
        """
        # Drop rows with bad temp or depth data (not sure why I did this, commented out
        # and replaced with dropped if any variable is nan)
        # self.df = self.df.dropna(how='any', subset=['DATETIME', 'TEMPERATURE', 'PRESSURE'])
        # Drop rows with any nan
        self.df = self.df.dropna(axis=0, how="any")
        try:
            self.df = self.df.set_index(["DATETIME"])
            self.ds = self.df.to_xarray().set_coords(["LATITUDE", "LONGITUDE"])
        except Exception as exc:
            self.logger.error(f"Could not convert df to ds for {self.filename}: {exc}")
            raise type(exc)(f"Could not convert df to ds in file read due to: {exc}") from exc

    def _identify_sensor_resets(self):
        """
        Creates a list of the reset codes, if any, that correspond to any rows with
        the default reset value (temp = 44.444).  This is later added as a global
        attribute to the xarray dataset.  This is kind of a mess now.
        """
        try:
            self.global_attrs["reset_codes_data"] = "None"
            self.global_attrs["reset_codes_timestamps"] = "None"
            self.global_attrs["reset_codes_index"] = "None"
            resetmask = np.isclose(
                self.df["TEMPERATURE"].to_numpy(), self.default_reset_value, 0.001
            )
            if resetmask.any():
                found_reset_codes = self.df.loc[resetmask, "PRESSURE"].to_numpy(dtype="int")
                found_reset_codes_timestamps = self.df.loc[resetmask].index.to_numpy(
                    dtype="datetime64[ns]"
                )
                found_reset_codes_index = np.where(resetmask)[0]
                self.global_attrs["reset_codes_data"] = ", ".join(str(x) for x in found_reset_codes)
                self.global_attrs["reset_codes_timestamps"] = ", ".join(
                    str(x) for x in found_reset_codes_timestamps
                )
                self.global_attrs["reset_codes_index"] = ", ".join(
                    str(x) for x in found_reset_codes_index
                )
        except Exception as exc:
            self.logger.error(f"Unable to calculate sensor resets for {self.filename}: {exc}")

    def _calc_header_rows(self, default_skiprows=13):
        """
        The datafile header size changes with different Mangopare firmware.
        Looks for startstring to indicate end of header.
        """
        start_line = False
        try:
            with open(self.filename) as f:
                for line_num, row_data in enumerate(f):
                    data = row_data.split(",")
                    if data[0] == self.startstring:
                        start_line = line_num
        except Exception as exc:
            # if it can't calculate the line to start at, use the default
            # will probably fail though
            if not start_line:
                start_line = default_skiprows
            self.logger.error(
                f"Could not calculate number of header rows, attempting to use default of {start_line}: {exc}"
            )
        return start_line

    def _load_global_attributes(self):
        # Add attributes from csv file header
        try:
            with open(self.filename) as f:
                for _ in range(self.start_line):
                    row = f.readline().split(",")
                    attr_name = row[0]
                    # extract units from attr_name and
                    # append to attr_val
                    res = re.findall(r"\(.*?\)", attr_name)
                    res = "" if not res else " " + res[0]
                    if attr_name == "Cellular upload position":
                        attr_val = str(row[1].strip()) + ", " + str(row[2].strip())
                    else:
                        attr_val = str(row[1].strip()) + res
                    # remove 'illegal' characters - fix raw string for regex
                    attr_name = re.sub(r"[\(\[].*?[\)\]]", "", attr_name).strip()
                    attr_name = re.sub(" ", "_", attr_name).lower()
                    self.ds.attrs[attr_name] = attr_val
            for name, value in self.global_attrs.items():
                self.ds.attrs[name] = value
        except Exception as exc:
            self.logger.error(f"Could not load global attributes for {self.filename} due to {exc}")
            raise type(exc)(f"Could not load global attributes during data file read due to: {exc}") from exc

    def run(self):
        # read file based on self.filetype
        self._read_mangopare_csv()
        self._format_df_data()
        self._identify_sensor_resets()
        self._convert_df_to_ds()
        self._load_global_attributes()
        return self.ds


class MangopareMetadataReader:
    """
    Read Mangopare fisher metadata in order to classify gear and
    to assign email addresses to Mangopare serial number.
    """

    def __init__(
        self,
        metafile="/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv",
        username=None,
        token=None,
        dateformat="%Y%m%dT%H%M%S",
        gear_class=None,
        logger=logging,
    ):
        if gear_class is None:
            gear_class = {"Bottom trawl": "mobile", "Potting": "stationary", "Long lining": "mobile", "Trawling": "mobile", "Midwater trawl": "mobile", "Purse seine netting": "mobile", "Bottom trawling": "mobile", "Research": "mobile", "Education": "mobile", "Bottom long line": "mobile", "Waka": "mobile"}
        if token is None:
            token = []
        if username is None:
            username = []
        self.metafile = metafile
        self.username = username
        self.token = token
        self.dateformat = dateformat
        self.gear_class = gear_class
        self.logger = logger

    def _load_fisher_metadata(self):
        """
        Read fisher metadata csv file provided by Zebra-Tech either from
        github or csv file path
        """
        try:
            if "raw.githubusercontent.com" in self.metafile:
                github_session = requests.Session()
                github_session.auth = (self.username, self.token)
                download = github_session.get(self.metafile).content
                self.fisher_metadata = pd.read_csv(
                    io.StringIO(download.decode("utf-8")),
                    on_bad_lines="skip",
                )
            else:
                with open(self.metafile, errors="replace") as f:
                    self.fisher_metadata = pd.read_csv(
                        f,
                        on_bad_lines="skip",
                    )
            # Convert date columns after reading
            for date_col in ["Date supplied", "Date returned"]:
                if date_col in self.fisher_metadata.columns:
                    self.fisher_metadata[date_col] = pd.to_datetime(
                        self.fisher_metadata[date_col], dayfirst=True, errors="coerce"
                    )
        except Exception as exc:
            self.logger.error(f"Could not load fisher metadata from {self.metafile}: {exc}")

    def _format_fisher_metadata(self):
        """
        Classifies gear to stationary or mobile based on gear type
        If no end date is specified, replace with today's date.
        """
        try:
            self.fisher_metadata["Gear Class"] = "unknown"
            self.fisher_metadata["Fishing method"] = self.fisher_metadata[
                "Fishing method"
            ].str.strip()
            for gvessel, gclass in self.gear_class.items():
                self.fisher_metadata.loc[
                    self.fisher_metadata["Fishing method"] == gvessel, "Gear Class"
                ] = gclass
            self.fisher_metadata["Date returned"] = self.fisher_metadata[
                "Date returned"
            ].replace({pd.NaT: datetime.now(timezone.utc)})
        except Exception as exc:
            self.logger.error(f"Could not load fisher metadata from {self.metafile}: {exc}")

    def run(self):
        # read file based on self.filetype
        try:
            self._load_fisher_metadata()
            self._format_fisher_metadata()
            return self.fisher_metadata
        except Exception as exc:
            self.logger.error(f"Could not load data from {self.metafile}: {exc}")
            raise type(exc)(f"Could not load data for {self.metafile} due to: {exc}") from exc
