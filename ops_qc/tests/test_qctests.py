import unittest
import numpy as np
from ops_qc.qc_tests_df import *


class TestQcTests(unittest.TestCase):

    def setUp(self):
        self.qcdf = pd.DataFrame()
        self.df = pd.DataFrame()
        self.df['TEMPERATURE'] = [14.5,13.8,13.7,13.6,13,13,25,13.1,13,12.9,12.6,12.6,12.6,12.6,12.6,12.6,12.9,12.8,12.9,13.2,13.3,13.6,13.7]
        self.df['PRESSURE'] = [1,2.5,4,5,7,12,14,14.4,15,16,16.5,16.6,16.5,16.7,16.6,20,0,14,12,9,8,5,3]
        self.df['LONGITUDE'] = [-181,-180,-360,-180,173.28393,173.283934,177,176,110,-110,-90,-89,180,190,260,300,360,360,361,362,363,365,366]
        self.df['LATITUDE'] = [-36,-36.01,-36.025,-36.031,-41.25707,-41.25708,-90,-91,-90,-105,-36.06,-37,-38,-52,89,90,100,90,87,86,85,84,83]
        self.df['DATETIME'] = np.array(['2021-08-02T06:37:14.000000000','2021-08-02T06:37:16.000000000',
       '2021-08-03T06:35:18.000000000', '2021-08-03T06:35:28.000000000',
       '2021-08-03T06:35:40.000000000', '2021-08-03T06:35:53.000000000',
       '2021-08-03T06:35:55.000000000', '2021-08-03T06:36:04.000000000',
       '2021-08-03T06:36:14.000000000', '2021-08-03T06:36:27.000000000',
       '2021-08-03T06:36:26.000000000', '2021-08-03T06:37:03.000000000',
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
        self.assertEqual(expected_vals_datetime,self.qcdf['flag_timing_gap'].tolist())
    
    def test_global_range(self):
        self.df['TEMPERATURE'] = [-3,-2,-1,0,13,13,25,13.1,13,12.9,12.6,12.6,12.6,12.6,15,20,25,30,32,33,34,35,36]
        self.df['PRESSURE'] = [1,2.5,4,5,7,12,14,14.4,15,16,16.5,16.6,16.5,16.7,1600,1610,2000,2100,12,9,8,5,3]
        global_range(self, ranges=None, fail_flag=[3,4])
        expected_vals_t = [4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,3,4,4,4]
        expected_vals_p = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,4,4,4,4,4,4,4]
        self.assertEqual(expected_vals_t,self.qcdf['flag_global_range_temp'].tolist())
        self.assertEqual(expected_vals_p,self.qcdf['flag_global_range_pres'].tolist())

    def test_impossible_location(self):
        impossible_location(self, lonrange=None, latrange=None, fail_flag=4, flag_name='flag_impossible_loc')
        expected_vals = [4,1,4,1,1,1,1,4,1,4,1,1,1,1,1,1,4,1,4,4,4,4,4]
        self.assertEqual(expected_vals,self.qcdf['flag_impossible_loc'].tolist())

    def test_remove_ref_location(self):
        remove_ref_location(self, bad_radius=5, ref_lat=-41.25707, ref_lon=173.28393, fail_flag=4, flag_name='flag_ref_loc')
        expected_vals = [1,1,1,1,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        self.assertEqual(expected_vals,self.qcdf['flag_ref_loc'].tolist())

    def test_datetime_increasing(self):
        datetime_increasing(self,fail_flag=4,flag_name='flag_datetime_inc')
        expected_vals = [4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4]
        self.assertEqual(expected_vals,self.qcdf['flag_datetime_inc'].tolist())