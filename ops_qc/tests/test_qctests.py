import unittest
import numpy as np
from ops_qc.qc_tests_df import *


class TestQcTests(unittest.TestCase):

    def setUp(self):
        self.qcdf = pd.DataFrame()
        self.df = pd.DataFrame()
        self.df['TEMPERATURE'] = [14.5,13.8,13.7,13.6,13,13,25,13.1,13,12.9,12.6,12.6,12.6,12.6,12.6,12.6,12.9,12.8,12.9,13.2,13.3,13.6,13.7]
        self.df['PRESSURE'] = [1,2.5,4,5,7,12,14,14.4,15,16,16.5,16.6,16.5,16.7,16.6,20,0,14,12,9,8,5,3]
        self.df['DATETIME'] = np.array(['2021-08-02T06:37:14.000000000','2021-08-02T06:37:16.000000000',
       '2021-08-03T06:35:18.000000000', '2021-08-03T06:35:28.000000000',
       '2021-08-03T06:35:40.000000000', '2021-08-03T06:35:53.000000000',
       '2021-08-03T06:35:55.000000000', '2021-08-03T06:36:04.000000000',
       '2021-08-03T06:36:14.000000000', '2021-08-03T06:36:27.000000000',
       '2021-08-03T06:36:58.000000000', '2021-08-03T06:37:03.000000000',
       '2021-08-03T06:37:10.000000000', '2021-08-03T06:37:16.000000000',
       '2021-08-03T06:37:22.000000000', '2021-08-03T06:37:32.000000000',
       '2021-08-03T06:37:37.000000000', '2021-08-03T06:37:40.000000000',
       '2021-08-03T06:38:15.000000000', '2021-08-03T06:38:25.000000000',
       '2021-08-03T06:38:44.000000000', '2021-08-03T06:38:45.000000000',
       '2021-08-03T19:25:39.000000000'], dtype='datetime64[ns]')


    def test_rate_of_change(self):
        rate_of_change_test(self, thresh=2, fail_flag=3)
        expected_peaks = [1,1,1,1,1,1,1,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        assert expected_peaks == self.qcdf['flag_roc'].tolist()

    def test_spike(self):
        spike(self, fail_flag=3)
        expected_peaks_pres = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,1,1,1,1,1,1]
        expected_peaks_temp = [3,1,1,1,1,1,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        self.assertEqual(expected_peaks_temp,self.qcdf['flag_spike_temp'].tolist())
        self.assertEqual(expected_peaks_pres,self.qcdf['flag_spike_pres'].tolist())

    def test_stuck_value(self):
        stuck_value(self, qc_vars=None, rep_num=5, fail_flag=2)
        expected_vals_temp = [1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,1,1,1,1,1,1,1,1]
        expected_vals_pres = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        self.assertEqual(expected_vals_temp,self.qcdf['flag_stuck_value_temp'].tolist())
        self.assertEqual(expected_vals_pres,self.qcdf['flag_stuck_value_pres'].tolist())

    def test_timing_gap(self):
        timing_gap(self, max_min=60, num_obs=5, fail_flag=3)
        expected_vals_datetime = [3,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3]
        print(len(expected_vals_datetime))
        print(len(self.qcdf['flag_timing_gap']))
        self.assertEqual(expected_vals_datetime,self.qcdf['flag_timing_gap'].tolist())