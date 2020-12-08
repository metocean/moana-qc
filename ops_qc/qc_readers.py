import numpy as np
import pandas as pd
from datetime import datetime
import logging
import subprocess
import io

from qc_utils import catch


class MangopareStandardReader(object):
    """
    Read Mangopare temperature and pressure data for applying quality control.
    Right now this is all done using pandas dataframes for consistency with
    the Berring Data Collective.
    Inputs:
        filetype: 'sensor' or 'fisherdata'

        Load Mangopare csv data into a pandas dataframe, then convert to xarray.
        Converts column names to be consistent with BDC QC.
        Inputs:
            filename: mangopare csv file to be read
            self.startstring: name of first column in order to skip header,
                example: startstring = 'DateTime (UTC)'
            self.dateformat: date format to convert to pd.datetime object
                example: dateformat = '%Y%m%dT%H%M%S'
        Output:
            self.ds = xarray dataset including data attributes

        To do: UPDATE GLOBAL ATTRIBUTES I.E. LIKE CORA.  Maybe global ATTRIBUTES
        variable (dictionary) is needed
    """

    def __init__(self,
                 filename,
                 filetype='sensor',
                 dateformat='%Y%m%dT%H%M%S',
                 startstring="DateTime (UTC)",
                 skip_rows=11,
                 logger=logging):
        self.filename = filename
        self.filetype = filetype
        self.dateformat = dateformat
        self.startstring = startstring
        self.skip_rows = skip_rows
        self.logger = logger

        self.global_attrs = {
            'Date quality controlled': datetime.utcnow().astimezone().strftime("%Y-%m-%dT%H:%M:%S %z"),
            'Quality control repository': 'https://github.com/metocean/ops-qc',
            'QC git revision': subprocess.check_output(['git', 'log', '-n', '1', '--pretty=tformat:%h-%ad', '--date=short']).strip(),
            'Raw data filename': self.filename
        }

    def _read_mangopare_csv(self):
        """
        Opens a mangopare csv file in pandas, formats the data, converts to xarray
        """
        try:
            self.start_line = self._calc_header_rows(default_skiprows=self.skip_rows)
        except Exception as exc:
            print('Could not calculate start row of csv data for {}. Traceback: {}'.format(self.filename, exc))

        try:
            self.df = pd.read_csv(
                self.filename, skiprows=self.start_line, error_bad_lines=False)
        except Exception as exc:
            print('Could not read file {} due to {}'.format(self.filename, exc))

    def _format_df_data(self):
        """
        Miscellaneous Mangopare data formatting
        """
        try:
            depth_col = [col for col in self.df.columns if (
                'Depth' or 'Pressure') in col]
            if len(depth_col) == 1:
                self.df.rename(columns={str(depth_col[0]): 'PRESSURE', 'DateTime (UTC)': 'DATETIME',
                                        'Lat': 'LATITUDE', 'Lon': 'LONGITUDE', 'Temperature C': 'TEMPERATURE'}, inplace=True)
            else:
                self.logger.error(
                    'Column name not recognized in {}'.format(self.filename))
            self.df['DATETIME'] = pd.to_datetime(
                self.df['DATETIME'], format=self.dateformat, errors='coerce')
            self.df['TEMPERATURE'] = [catch(lambda:float(t))
                                      for t in self.df['TEMPERATURE']]

            # Drop rows with bad temp or depth data
            self.df = self.df.dropna(
                how='any', subset=['DATETIME', 'TEMPERATURE', 'PRESSURE'])

            # Convert 0 lat/lon to nan, since 0 is bad value, but don't drop
            self.df['LONGITUDE'].loc[self.df['LONGITUDE'] == 0] = np.nan
            self.df['LATITUDE'].loc[self.df['LATITUDE'] == 0] = np.nan
        except Exception as exc:
            print('Formatting of data failed for {}.  Traceback: {}'.format(self.filename, exc))

    def _convert_df_to_ds(self):
        """
        Sets dims and coords, converts to xaxrray dataset.
        """
        try:
            self.df = self.df.set_index(['DATETIME'])
            self.ds = self.df.to_xarray().set_coords(['LATITUDE', 'LONGITUDE'])
        except Exception as exc:
            print('Could not convert df to ds for {}. Traceback: {}'.format(self.filename, exc))

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
            self.logger.error('Could not calculate number of header rows, attempting to use default of {}. Traceback: {}'.format(start_line, exc))
        return(start_line)

    def _load_global_attributes(self):
        # Add attributes from csv file header
        try:
            f = open(self.filename)
            for i in range(self.start_line):
                row = f.readline().split(',')
                self.ds.attrs[row[0]] = row[1].strip()
            for name, value in self.global_attrs.items():
                self.ds.attrs[name] = value
        except Exception as exc:
            print('Could not load global attributes for {} due to {}'.format(self.filename, exc))

    def run(self):
        # read file based on self.filetype
        try:
            self._read_mangopare_csv()
            self._format_df_data()
            self._convert_df_to_ds()
            self._load_global_attributes()
            return(self.ds)
        except Exception as exc:
            self.logger.error('Could not load data from {}. Traceback: {}'.format(self.filename, exc))


class MangopareMetadataReader(object):
    """
    Read Mangopare fisher metadata in order to classify gear and
    to assign email addresses to Mangopare serial number.
    """

    def __init__(self,
                 metafile='/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv',
                 dateformat='%Y%m%dT%H%M%S',
                 gear_class=None,
                 logger=logging):
        if gear_class is None:
            gear_class = {'Bottom trawl': 'mobile', 'Potting': 'stationary',
                          'Long lining': 'mobile', 'Trawling': 'mobile', 'Midwater trawl': 'mobile'}
        self.metafile = metafile
        self.dateformat = dateformat
        self.gear_class = gear_class
        self.logger = logger

    def _load_fisher_metadata(self):
        """
        Read fisher metadata csv file provided by Zebra-Tech
        """
        try:
            self.fisher_metadata = pd.read_csv(io.open(self.metafile, errors='replace'), error_bad_lines=False, parse_dates=[
                                               "Date supplied", "Date returned"], date_parser=lambda x: pd.to_datetime(x, format="%d/%m/%Y"))
        except Exception as exc:
            self.logger.error(
                'Could not load fisher metadata from {}'.format(self.metafile))
            raise exc

    def _format_fisher_metadata(self):
        """
        Classifies gear to stationary or mobile based on gear type
        If no end date is specified, replace with today's date.
        """
        try:
            self.fisher_metadata['Gear Class'] = 'unknown'
            for gvessel, gclass in self.gear_class.items():
                self.fisher_metadata.loc[self.fisher_metadata['Fishing method']
                                         == gvessel, 'Gear Class'] = gclass
            self.fisher_metadata['Date returned'].replace(
                {pd.NaT: datetime.utcnow()}, inplace=True)
        except Exception as exc:
            self.logger.error(
                'Could not load fisher metadata from {}'.format(self.metafile))
            raise exc

    def run(self):
        # read file based on self.filetype
        try:
            self._load_fisher_metadata()
            self._format_fisher_metadata()
            return(self.fisher_metadata)
        except Exception as exc:
            self.logger.error('Could not load data from {}. Traceback: {}'.format(self.metafile, exc))
