import unittest
import numpy as np
from ops_qc.utils import calc_speed, load_yaml


class TestVariousUtils(unittest.TestCase):

    def setUp(self):
        self.df = np.array([1.00,1.20,1.50,1.60,1.80,1.90,1.90,1.80,1.80,
                          1.60,1.80,1.40,1.20,1.00,1.10,1.50,1.90,2.50,
                          3.00,3.00,2.80,2.50,2.00])
        self.tm02 = np.array([10, 15, 12, 12, 12, 12, 12, 15, 15, 15, 15,
                             15, 15, 12, 12, 13, 15, 14, 15, 12, 13, 12, 11,])


    def test_peak_detection(self):
        peaks = detect_peaks(self.hs, edge='falling', mpd=3)
        expected_peaks = [6,10,19]
        assert expected_peaks == peaks.tolist()

    def test_calculate_storm_hmp(self):
        result = calculate_storm_Hmp(self.hs, self.tm02)
        assert result.any()
