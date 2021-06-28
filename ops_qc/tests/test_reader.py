import unittest
import os
import pandas as pd
import xarray as xr

from ops_qc.readers import MangopareStandardReader
from ops_qc.readers import MangopareMetadataReader

class TestMangopareStandardReader(unittest.TestCase):

    def setUp(self):
        self.filename = 'tests/testdata/MOANA_0038_13_210624041106.csv'

    def test_MangopareStandardReader(self):
        ds = MangopareStandardReader(self.filename).run()
        assert isinstance(ds,xr.core.dataset.Dataset)
        var_list = list(ds.keys())
        coord_list = list(ds.coords)
        expected_vars = ['PRESSURE','TEMPERATURE']
        expected_coords = ['LATITUDE','LONGITUDE','DATETIME']
        assert all(var_name in var_list for var_name in expected_vars)
        assert all(var_name in coord_list for var_name in expected_coords)
