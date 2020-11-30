import pandas as pd
import numpy as np
from datetime import datetime
import logging
import qc_tests_df as qctests
from qc_utils import catch

#######################################################################################################################
# QC
#######################################################################################################################

class QC_apply(object):
    '''Base class for observational data quality control.
    Input dataframe with LONGITUDE, LATITUDE, DATETIME, PRESSURE, TEMPERATURE
    of same shape and applies QC, designed for instruments mounted on fishing gear.
    Converts dataset to dataframe for consistency with BDC QC code.
    At some point might change all QC to ds so we don't have to switch
    back and forth.
    '''
    def __init__(self,
                ds = ds,
                test_list = None,
                save_flags = False,
                convert_p_to_z = True,
                default_latitude = -40,
                test_order = False,
                logger = logging):

        self.ds = ds
        self.test_list = test_list
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.default_latitude = default_latitude
        self.test_order = test_order
        self.logger = logging
        self.df = self.ds.to_dataframe()

    def _run_qc_tests(self):
        for testname in self.test_list:
            try:
                self.qc_test = getattr(qctests,testname)
                self.qc_test()
            else:


    def _merge_df_and_ds(self):
        '''
        Converts pandas dataframe back to xarray, adds back in
        attributes from original ds.  Updates attributes.
        '''

    def _global_qc_flag(self):
        '''
        Individual QC tests record qc flag in flag_* column.
        Take the maximum value to determine overall qc flag
        for each measurement.
        '''
        qc_col = [col for col in df if col.startswith('flag')]
        self.df['qc_flag'] = self.df[qc_col].max(axis=0)

    def run(self):
        # initialize global QC flag with zero (no QC'd value)
        self.flag = np.zeros_like(df['LONGITUDE'])
        # run df and ds test
        if self.qc_tests:
            self._run_qc_tests()
        self._global_qc_flag()
