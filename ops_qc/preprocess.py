import pandas as pd
import numpy as np
import xarray as xr
import logging
import datetime
from ops_qc.utils import load_yaml
#from ops_core.utils import import_pycallable, catch_exception

# Note DATETIME not included below because xaxrray
# encodes datetime automatically
# var_attr_info = {
#     'LATITUDE': ['latitude', 'degree_north'],
#     'LONGITUDE': ['longitude', 'degree_east'],
#     'TEMPERATURE': ['sea_water_temperature', 'degree_C'],
#     'PRESSURE': ['sea_water_pressure', 'dbar'],
#     'PHASE': ['fishing_deployment_phase', 'na']
# }


class PreProcessMangopare(object):
    """
    Mangopare position processing and fishing gear classification.
    Inputs:
        ds: xarray dataset including data to be QC'd
        metadata: pandas dataframe with Mangopare fisher metadata
        These are generated using qc_readers.py, see for defaults.
    """

    def __init__(self,
                 ds,
                 fisher_metadata,
                 filename,
                 attr_file='attribute_list.yml',
                 attr_dict_name='var_attr_info',
                 metadata_columns={'gear_class': 'Gear Class', 'vessel_email': 'Contact email',
                                   'vessel_name': 'Vessel name', 'email_status': 'Email Status',
                                   'email_frequency': 'Email Frequency', 'expected_deck_unit_serial_number': 'Deck unit serial number'},
                 surface_pressure=5,
                 add_sitename=True,
                 logger=logging):

        self.ds = ds
        self.fisher_metadata = fisher_metadata
        self.filename = filename
        self.attr_file = attr_file
        self.attr_dict_name = attr_dict_name
        self.metadata_columns = metadata_columns
        self.surface_pressure = surface_pressure
        self.add_sitename = add_sitename
        self.logger = logging
        self.filename = self.ds.attrs['raw_data_filename']
        self.status_dict = {}

    def _classify_gear(self):
        """
        Takes fisher metadata spreadsheet info and matches it with the file being
        processed.  Also adds vessel email to dataset attributes.
        Inputs include self.fisher_metadata from qc_readers.load_fisher_metadata and
        self.df from qc_readers.load_moana_standard/
        """
        self.ds.attrs['gear_class'] = 'unknown'
        try:
            ms = int(self.ds.attrs['moana_serial_number'])
            sn_data = self.fisher_metadata.loc[self.fisher_metadata['Mangopare serial number'] == ms]
            t_min = pd.to_datetime(np.min(self.ds['DATETIME']).values)
            t_max = pd.to_datetime(np.max(self.ds['DATETIME']).values)
            time_check = 0
            for _, row in sn_data.iterrows():
                # round max date to the first minute of the next day in spreadsheet
                if t_min >= row['Date supplied'] and t_max <= pd.to_datetime(row['Date returned'].date()+datetime.timedelta(days=1)):
                    for attrname, rowname in self.metadata_columns.items():
                        self.ds.attrs[attrname] = row[rowname]
                    try:
                        self.ds.attrs['vessel_id'] = int(row['Vessel id'])
                    except:
                        self.ds.attrs['vessel_id'] = 'NA'
                    try:
                        self.ds.attrs['expected_deck_unit_serial_number'] = int(
                            self.ds.attrs['expected_deck_unit_serial_number'])
                    except:
                        pass
                    time_check += 1
            if time_check < 1:
                self.status_dict.update(
                    {'failed': 'yes', 'failure_mode': 'No valid time range in fisher metadata.'})
                self.logger.info(
                    f'No valid time range found in fisher metadata for {self.filename}.')
            if time_check > 1:
                self.status_dict.update(
                    {'failed': 'yes', 'failure_mode': 'Multiple entries in fisher metadata for this SN and time range.'})
                self.logger.error(
                    'Multiple entries found for this SN and time range in fisher metadata, skipping {}.'.format(self.filename))
        except Exception as exc:
            self.logger.info(
                'Gear Class calculation failed, labeled as unknown: {}'.format(exc))
            self.status_dict.update(
                {'failed': 'yes', 'failure_mode': 'Could not assign attribute(s) from csv header.'})

    def _calc_positions(self, surface_pressure=5):
        """
        Calculate locations for either stationary or mobile gear.
        Current state of this code assumes all stationary locations
        in one CSV file are the SAME.  NOT NECESSARILY TRUE!  Hence
        the commented out regions...eventually will use those.
        """
        try:
            if self.ds.attrs['gear_class'] == 'stationary':
                # Remove rows with nan lat/lon, which we kept in reader
                self.ds = self.ds.dropna(how='any', dim='DATETIME')
                # use self.surface_pressure if it exists
                try:
                    surface_pressure = self.surface_pressure
                except:
                    pass
                # Find when gear comes to/near the surface
                ds2 = self.ds.where(
                    self.ds['PRESSURE'] < surface_pressure, drop=True)
                # if len(ds2.lat.values)==[1,2]:
                lat = np.nanmean(ds2.LATITUDE.values)
                lon = np.nanmean(ds2.LONGITUDE.values)
                # else:
                # haven't worked out yet what to do if there's
                # lots of "surface" lat/lon pairs...that will go here:
                #lat = np.array(ds2.lat.values)
                #lon = np.array(ds2.lon.values)
                lons = np.ones_like(self.ds['LONGITUDE'])*lon
                lats = np.ones_like(self.ds['LATITUDE'])*lat
                self.ds['LATITUDE'] = xr.DataArray(lats, dims=['DATETIME'])
            if self.ds.attrs['gear_class'] == 'mobile':
                lons = self.ds['LONGITUDE']
            # convert to 0-360 for both stationary and mobile gear:
            lons = [l % 360 for l in lons]
            self.ds['LONGITUDE'] = xr.DataArray(lons, dims=['DATETIME'])
        except Exception as exc:
            self.logger.error(
                f"Position could not be calculated for {self.filename}: {exc}")
            raise exc

    def _find_bottom(self, cutoff='4 minutes'):
        """
        Uses timedelta to assign profile (PROF) or deployed (DEPL) status
        to each datapoint in fishing gear deployment.  Used to estimate average bottom or fishing
        temperature.
        Currently a big mess.  But xarray was being annoying and I don't
        know why I can't figure out how to subtract two times to get a
        datetime timedelta NOT an int!!!
        """
        try:
            cutoff = pd.Timedelta(cutoff)
            df = self.ds.to_dataframe()
            df.reset_index(inplace=True)
            times = df['DATETIME']
            t_delta = (times-times.shift()).fillna(pd.Timedelta('0 days'))
            cat = np.chararray(len(self.ds['TEMPERATURE']))
            cat[:] = 'D'
            cat[t_delta < cutoff] = 'P'
        except Exception as exc:
            cat = np.empty(len(self.ds['TEMPERATURE']))
            self.logger.error(
                'Bottom not found for {}, np.nan applied instead: {}'.format(self.filename, exc))

        self.ds['PHASE'] = xr.Variable(dims='DATETIME', data=cat)
        self.ds['PHASE'].attrs.update({'flag_values': [
                                      'P', 'D'], 'flag_meanings': 'P indicates the measurement was classified as a profile, D indicates deployed (i.e. bottom, fishing)'})

    def _add_variable_attrs(self):
        """
        Loads local variable attributes from attribute file.
        [Uses the local variable dictionary at the start of this file
        to specify the name and units for each var.]
        Example dictionary: var_attr_info = {'LATITUDE':['latitude','units']}
        """
        try:
            var_attr_info = load_yaml(self.attr_file, self.attr_dict_name)
            for var, [standard_name, units] in var_attr_info.items():
                if var in self.ds.keys():
                    if standard_name:
                        self.ds[var].attrs.update(
                            {'standard_name': standard_name})
                    if units:
                        self.ds[var].attrs.update({'units': units})
        except Exception as exc:
            self.logger.error(
                'Could not assign variable attributes for {}: {}'.format(self.filename, exc))

    def _set_sitename(self):
        """
        Add site_name to dataset attributes for use in ingestion into the
        obs-api. If vessel_id is provided use that.  Otherwise, create
        a sitename of form NA{mangopare sn}DU{deck unit sn} which should
        be unique for each vessel (but not guaranteed).
        """
        if not self.add_sitename:
            sitename='NA'
        elif self.ds.attrs['vessel_id']=='NA':
            sitename=f'msn{self.ds.attrs["moana_serial_number"]}du{self.ds.attrs["deck_unit_serial_number"]}'
        else:
            sitename=f'vid{self.ds.attrs["vessel_id"]}'
        self.ds.attrs['site_name']=sitename

    def run(self):
        try:
            self._classify_gear()
            if self.ds.attrs['gear_class'] != 'unknown':
                self._calc_positions()
                self._find_bottom()
                self._add_variable_attrs()
                self._set_sitename()
            return(self.ds, self.status_dict)
        except Exception as exc:
            self.logger.error(
                'Could not preprocess data from {}: {}'.format(self.filename, exc))
