import logging
import pandas as pd
import xarray as xr
from qc_utils import load_yaml


#######################################################################################################################
# QC
#######################################################################################################################

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
                 ds=ds,
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
        flag_attrs = self._load_qc_attrs(self.attr_file)
        qc_attr_info = flag_attrs[]
        if self.qcdf:
            for flag_name in self.qcdf.keys():
                self.ds[flag_name] = xr.Variable(dims='DATETIME', data=self.qcdf[flag_name], 'units'=, 'standard_name'= , 'long_name'=)


    def _assign_qc_attributes(self,flag_attrs,flag_name):
        """
        Uses qc attributes and flag information from
        _load_qc_attrs and applies it to each flag in the
        self.ds dataset
        """

    def _load_qc_attributes(self):
        """
        Assign variable attributes to QC flags
        """
        for dictionary in load_yaml(self.attr_file):
            qc_attr_info = flag_attrs['qc_attr_info']

        return(flag_attrs)

    def _global_qc_flag(self):
        """
        Individual QC tests record qc flag in flag_* column.
        Take the maximum value to determine overall qc flag
        for each measurement.
        """
        self.qc_flag = np.zeros_like(self.df['LONGITUDE'])
        qc_col = [col for col in self.df if col.startswith('flag')]
        self.df['qc_flag'] = self.df[qc_col].max(axis=0)

    def run(self):
        # initialize global QC flag with zero (no QC'd value)
        # run df and ds test
        if self.test_list:
            self._run_qc_tests()
        self._global_qc_flag()
        if self._tests_not_applied:
            self.logger.error('Unable to apply the following qc tests: {}'.format(self._tests_not_applied))
