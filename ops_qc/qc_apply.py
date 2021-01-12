import logging
import pandas as pd
import xarray as xr
from qc_utils import load_yaml

class QcApply(object):
    """
    Base class for observational data quality control.
    Input dataframe with LONGITUDE, LATITUDE, DATETIME, PRESSURE, TEMPERATURE
    of same shape and applies QC, designed for instruments mounted on fishing gear.
    Converts dataset to dataframe for consistency with BDC QC code.
    At some point might change all QC to ds so we don't have to switch
    back and forth.
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
        self.df = self.ds.to_dataframe()

    def _run_qc_tests(self):
        self._success_tests = []
        self._tests_not_applied = []
        for test_name in self.test_list:
            try:
                # from qc_tests_df import *
                # needed for this to work
                test_name()
                self._success_tests.append(test_name)
                # use this if importing module only
            #                qc_test = getattr(qctests,test_name)
            #                qc_test()
            except Exception as exc:
                self._tests_not_applied.append(test_name)
                self.logger.error('Could not apply QC test {}.  Traceback: {}'.format(test_name,exc))

    def _merge_df_and_ds(self):
        """
        Converts pandas dataframe back to xarray, adds back in
        attributes from original ds.  Updates attributes.
        """
        try:
            flag_attrs = load_yaml(self.attr_file,'qc_attr_info')
            qc_flag_info = load_yaml(self.attr_file,'qc_flag_info')
        except Exception as exc:
            self.logger.error('Could not load qc flag attribute data from {}. Traceback: {}'.format(self.attr_file,exc))
        try:
            if self.qcdf:
                for flag_name in self.qcdf.keys():
                    self.ds[flag_name] = xr.Variable(dims='DATETIME', data=self.qcdf[flag_name])
                    self._assign_qc_attributes(flag_attrs, flag_name, qc_flag_info)
        except Exception as exc:
            self.logger.error('Could not apply attributes to qc flag {}. Traceback: {}'.format(flag_name,exc))


    def _assign_qc_attributes(self,flag_attrs,flag_name,qc_flag_info):
        """
        Uses qc attributes and flag information from
        _load_qc_attrs and applies it to each flag in the
        self.ds dataset
        """
        long_name = flag_attrs[flag_name][0]
        standard_name = flag_attrs[standard_name]
        flag_values = [str(val).encode() for val in flag_info['flag_values']]
        flag_meanings = qc_flag_info['flag_meanings']
        self.ds[flag_name].attrs.update({'long_name': long_name,
                                           'standard_name': standard_name,
                                           'flag_values': flag_values,
                                           'flag_meanings': flag_meanings
                                           })
    def _global_qc_flag(self):
        """
        Individual QC tests record qc flag in flag_* column.
        Take the maximum value to determine overall qc flag
        for each measurement.
        """
        try:
            self.qcdf['qc_flag'] = np.zeros_like(self.df['LONGITUDE'])
            self.qcdf['qc_flag'] = self.qcdf.max(axis=0)
        except Exception as exc:
            self.logger.error('Unable to calculate global quality control flag. Traceback: {}'.format(exc))

    def run(self):
        try:
            if self.test_list:
                self._run_qc_tests()
            else:
                self.logger.error('No QC tests in list of tests, skipping QC')
            self._global_qc_flag()
            self._merge_df_and_ds()
            if self._tests_not_applied:
                self.logger.error('Unable to apply the following qc tests: {}'.format(self._tests_not_applied))
            return(self.ds)
        except Exception as exc:
            self.logger.error('QC testing failed.  Traceback: {}'.format(exc))
