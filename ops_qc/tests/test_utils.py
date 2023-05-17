import unittest
import numpy as np
import pandas as pd
from datetime import datetime
from ops_qc.utils import haversine, calc_speed


class TestVariousUtils(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame()
        self.df['LATITUDE'] = np.array([-36,-37,-38,-39,-42,-45])
        self.df['LONGITUDE'] = np.array([168,169,175,180,183,185])
        start_date = datetime.strptime('2020-10-05','%Y-%m-%d')
        self.df['DATETIME'] = pd.date_range(start_date,periods=6).tolist()


    def test_haversine(self):
        dist_value = haversine(lat1=-36.5, lon1=160, lat2=-38, lon2=165)
        expected_value = np.round(472.8638055302368,5)
        assert expected_value == np.round(dist_value,5)

    def test_calc_speed(self):
        df = calc_speed(self.df,units='kts')
        speed_knots = df['speed'].dropna().to_numpy()
        df = calc_speed(self.df,units='mph')
        speed_mph = df['speed'].dropna().to_numpy()
        expected_knots = [3.2097104442373157, 12.165883268608592, 10.10229090435196, 9.426965412500206, 8.335832484291391]
        assert np.allclose(speed_knots,expected_knots)
        expected_mph = [speed*1.15077867312 for speed in speed_knots]
        assert np.allclose(speed_mph,expected_mph)


