import pandas as pd
import numpy as np
import xarray as xr
import logging
import datetime
from ops_qc.utils import load_yaml

class PreProcessMangopare(object):
    """
    Mangopare position processing and fishing gear classification.
    Inputs:
        ds: xarray dataset including data to be QC'd
        metadata: pandas dataframe with Mangopare fisher metadata
        These are generated using qc_readers.py, see for defaults.
        status_dict: dictionary with file processing status info,
        if not already provided, will start with empty dict.  If
        provided, will update dict with new processing info.
    """

    def __init__(self,
                 ds,
                 fisher_metadata,
                 attr_file='attribute_list.yml',
                 var_attr_dict_name='var_attr_info',
                 global_attr_dict_name='global_attr_info',
                 metadata_columns={
                    'gear_class': 'Gear Class', 
                    'vessel_email': 'Contact email',
                    'vessel_name': 'Vessel name', 
                    'email_status': 'Email Status',               
                    'email_frequency': 'Email Frequency', 
                    'expected_deck_unit_serial_number': 'Deck unit serial number',
                    'deployment_method':'Fishing method'},
                 surface_pressure=5,
                 add_sitename=True,
                 status_dict={},
                 logger=logging):

        self.ds = ds
        self.fisher_metadata = fisher_metadata
        self.attr_file = attr_file
        self.var_attr_dict_name = var_attr_dict_name
        self.global_attr_dict_name = global_attr_dict_name
        self.metadata_columns = metadata_columns
        self.surface_pressure = surface_pressure
        self.add_sitename = add_sitename
        self.status_dict = status_dict
        self.logger = logging
        self.filename = self.ds.attrs['raw_data_filename']

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
            self.status_dict.update(self.ds.attrs)
            t_min = pd.to_datetime(np.min(self.ds['DATETIME']).values)
            t_max = pd.to_datetime(np.max(self.ds['DATETIME']).values)
        except Exception as exc:
            self.logger.error(
                'Could not calculate time range or sn data: {}'.format(exc))
            raise type(exc)(f'Could not calculate time range or sn data, len(DATETIME)={len(self.ds.DATETIME)} due to: {exc}')
            #self.status_dict.update(
            #    {'failed': 'yes', 'failure_mode': f'Could not calculate time range or sn data, len(DATETIME)={len(self.ds.DATETIME)}', 'detailed_error':str(exc)})
        try:
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
                    self.status_dict.update(self.ds.attrs)
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
            self.logger.error(
                'Gear Class calculation failed, labeled as unknown: {}'.format(exc))
            raise type(exc)(f'Could not assign attribute(s) from csv header due to: {exc}')
            #self.status_dict.update(
            #    {'failed': 'yes', 'failure_mode': 'Could not assign attribute(s) from csv header.', 'detailed_error':str(exc)})

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
            var_attr_info = load_yaml(self.attr_file, self.var_attr_dict_name)
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

    def _add_global_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        try:
            global_attr_info = load_yaml(
                self.attr_file, self.global_attr_dict_name)
            for var, varinfo in global_attr_info.items():
                self.ds.attrs[var] = varinfo
        except Exception as exc:
            self.logger.error(
                'Could not assign global attributes for {}: {}'.format(self.filename, exc))

    def _set_sitename(self):
        """
        Add site_name to dataset attributes for use in ingestion into the
        obs-api. If vessel_id is provided use that.  Otherwise, create
        a sitename of form NA{mangopare sn}DU{deck unit sn} which should
        be unique for each vessel (but not guaranteed).
        """
        try:
            if not self.add_sitename:
                sitename = 'NA'
            elif self.ds.attrs['vessel_id'] == 'NA':
                sitename = f'msn{self.ds.attrs["moana_serial_number"]}du{self.ds.attrs["deck_unit_serial_number"]}'
            else:
                sitename = f'vid{self.ds.attrs["vessel_id"]}'
            self.ds.attrs['platform_code'] = sitename
        except Exception as exc:
            self.logger.error('Could not assign sitename/platform code.')

    def run(self):
        # try:
        self._classify_gear()
        if self.ds.attrs['gear_class'] != 'unknown':
            # self._calc_positions()
            self.ds = self.ds.dropna(how='any', dim='DATETIME')
            self._find_bottom()
            self._add_variable_attrs()
            self._set_sitename()
            self._add_global_attrs()
            self.status_dict.update(self.ds.attrs)
        return (self.ds, self.status_dict)
        # except Exception as exc:
        #     self.logger.error(
        #         'Could not preprocess data from {}: {}'.format(self.filename, exc))
        #     raise type(exc)(f'Could not preprocess data due to: {exc}')

