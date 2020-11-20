import pandas as pd
import numpy as np
from datetime import datetime
import logging
import qc_tests_df as qcdf
import qc_test_ds as qcds
from qc_utils import catch

#######################################################################################################################
# QC
#######################################################################################################################

class QC_apply(object):
    '''Base class for observational data quality control.   
    Input dataframe with LONGITUDE, LATITUDE, DATETIME, PRESSURE, TEMPERATURE 
    of same shape and applies QC, designed for instruments mounted on fishing gear.
    Options for test_list: classify_gear, calc_stationary_loc, find_bottom, gear_type,
    Note that test_list MUST GO IN THE ORDER ABOVE.
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

    def _run_pre_processing(self):
        try:
            self.qc_test = getattr(qcds,testname)
            self.qc_test()
        except:
            self.logger.error('Test {} failed on {}'.format(testname,self.filename))
    
    def _run_qc_tests(self):
        for testname in self.test_list:
            try:
                self.qc_test = getattr(qcdf,testname)
                self.qc_test()
            else: 


    def merge_qc(self):

        

    def run(self):
        # initialize global QC flag with zero (no QC'd value)
        self.flag = np.zeros_like(df['LONGITUDE'])
        # run df and ds test
        if self.qc_tests:
            self._run_qc_tests()
        # convert pressure to depth if needed