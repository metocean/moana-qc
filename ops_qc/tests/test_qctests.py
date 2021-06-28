import unittest
import numpy as np
from ops_qc.qc_tests_df import *


class TestQcTests(unittest.TestCase):

    def setUp(self):
        self.qcdf = pd.DataFrame()
        self.df = pd.DataFrame()
        self.df['TEMPERATURE'] = [14.5,13.8,13.7,13.6,13,13,25,13.1,13,12.9,12.6,12.6,12.6,12.6,12.6,12.6,12.9,12.8,12.9,13.2,13.3,13.6,13.7]
        self.df['PRESSURE'] = [1,2.5,4,5,7,12,14,14.4,15,16,16.5,16.6,16.5,16.7,16.6,20,0,14,12,9,8,5,3]

    def test_rate_of_change(self):
        rate_of_change_test(self, thresh=2, fail_flag=3)
        expected_peaks = [1,1,1,1,1,1,1,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        assert expected_peaks == self.qcdf['flag_roc'].tolist()

    def test_spike(self):
        spike(self, fail_flag=3)
        expected_peaks = [3,1,1,1,1,1,3,1,1,1,1,1,1,1,1,1,3,1,1,1,1,1,1]
        assert expected_peaks == self.qcdf['flag_spike'].tolist()

    def test_stuck_value(self):
        stuck_value(self, qc_vars=None, rep_num=5, fail_flag=2)
        expected_vals = [1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,1,1,1,1,1,1,1,1]
        assert expected_vals == self.qcdf['flag_stuck_value'].tolist()
