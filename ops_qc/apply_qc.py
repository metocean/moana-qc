import logging
import pandas as pd
import xarray as xr
import numpy as np
from ops_qc.utils import load_yaml
import qc_tests_df as qc_tests


class QcApply(object):
    """
    Base class for observational data quality control.
    Input dataframe with LONGITUDE, LATITUDE, DATETIME, PRESSURE, TEMPERATURE
    of same shape and applies QC, designed for instruments mounted on fishing gear.
    Converts dataset to dataframe for consistency with BDC QC code.
    At some point might change all QC to ds so we don't have to switch
    back and forth.  Or change all qc flags to a list/dict which would make way more sense.
    """

    def __init__(self,
                 ds,
                 test_list=None,
                 save_flags=False,
                 convert_p_to_z=True,
                 default_latitude=-40,
                 attr_file='attribute_list.yml',
                 logger=logging):

        self.ds = ds
        self.test_list = test_list
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.default_latitude = default_latitude
        self.attr_file = attr_file
        self.logger = logging
        self.df = self.ds.to_dataframe().reset_index()
        self.flag_category = {}

    def _run_qc_tests(self):
        """
        Applies all qc tests from test_list and saves flags in
        self.qcdf dataframe.  Should probably be saving flags
        to a dict instead...
        """
        self._success_tests = []
        self._tests_not_applied = []
        # initialize dataframe to hold qc flags
        self.qcdf = pd.DataFrame()
        for test_name in self.test_list:
            try:
                # from qc_tests_df import *
                # needed for this to work
                #test_name()

                # use this if importing module only
                qc_test = getattr(qc_tests, test_name)
                qc_test(self)
                self._success_tests.append(test_name)
            except Exception as exc:
                self._tests_not_applied.append(test_name)
                self.logger.error(
                    'Could not apply QC test {}.  Traceback: {}'.format(test_name, exc))

    def _merge_df_and_ds(self):
        """
        Converts pandas dataframe back to xarray, adds back in
        attributes from original ds.  Updates attributes.
        """
        try:
            if len(self.qcdf.keys()) > 0:
                # if save_flags, add all qc_flags to ds
                # otherwise, only save global qc_flag
                if self.save_flags:
                    flag_list = self.qcdf.keys()
                else:
                    flag_list = self.global_flag_list
                for flag_name in flag_list:
                    self.ds[flag_name] = xr.Variable(
                        dims='DATETIME', data=self.qcdf[flag_name])
                    self._assign_qc_attributes(
                        self.flag_attrs, flag_name, self.qc_flag_info)
                self.ds.attrs['qc_tests_applied'] = str(self._success_tests)
                self.ds.attrs['qc_tests_failed'] = str(
                    self._tests_not_applied)
        except Exception as exc:
            self.logger.error(
                'Could not apply attributes to qc flags. Traceback: {}'.format(exc))

    def _load_qc_attrs(self):
        """
        Loads qc variable attributes from attribute_list file
        """
        try:
            self.flag_attrs = load_yaml(self.attr_file, 'qc_attr_info')
            self.qc_flag_info = load_yaml(self.attr_file, 'qc_flag_info')
            for flag_name in self.qcdf.keys():
                self.flag_category.update(
                    {flag_name: self.flag_attrs[flag_name][1]})
        except Exception as exc:
            self.logger.error('Could not load qc flag attribute data from {}. Traceback: {}'.format(
                self.attr_file, exc))

    def _assign_qc_attributes(self, flag_attrs, flag_name, flag_info):
        """
        Uses qc attributes and flag information from
        _load_qc_attrs and applies it to each flag in the
        self.ds dataset
        """
        try:
            long_name = flag_attrs[flag_name][0]
            standard_name = flag_attrs['standard_name']
            flag_values = [str(val).encode()
                           for val in flag_info['flag_values']]
            flag_meanings = flag_info['flag_meanings']
            self.ds[flag_name].attrs.update({'long_name': long_name,
                                             'standard_name': standard_name,
                                             'flag_values': flag_values,
                                             'flag_meanings': flag_meanings
                                             })
        except Exception as exc:
            self.logger.error(
                'Could not assign qc attribute {} due to {}, check that it exists in attribute yaml.'.format(flag_name, exc))

    def _global_qc_flag(self):
        """
        Individual QC tests record qc flag in flag_* column.
        Take the maximum value to determine overall qc flag
        for each measurement.
        """
        try:
            #import ipdb; ipdb.set_trace()
            self.qcdf['QC_FLAG'] = np.zeros_like(self.df['LONGITUDE'])
            self.qcdf['QC_FLAG'] = self.qcdf.max(axis=1).astype('int')
            self.global_flag_list = ['QC_FLAG']
            for flag_name, category in self.flag_category.items():
                if category == 'None':
                    continue
                if category not in self.global_flag_list:
                    self.global_flag_list.append(category)
                if category not in list(self.qcdf.keys()):
                    self.qcdf[category] = self.qcdf[flag_name]
                    continue
                self.qcdf[category] = self.qcdf[[
                    category, flag_name]].max(axis=1)
        except Exception as exc:
            self.logger.error(
                'Unable to calculate global quality control flag. Traceback: {}'.format(exc))

    def run(self):
        try:
            if self.test_list:
                self._run_qc_tests()
            else:
                self.logger.error('No QC tests in list of tests, skipping QC')
            self._load_qc_attrs()
            self._global_qc_flag()
            self._merge_df_and_ds()
            if self._tests_not_applied:
                self.logger.error('Unable to apply the following qc tests: {}'.format(
                    self._tests_not_applied))
            return(self.ds)
        except Exception as exc:
            self.logger.error('QC testing failed.  Traceback: {}'.format(exc))
