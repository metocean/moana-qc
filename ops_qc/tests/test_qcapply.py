import unittest
import os
import pandas as pd
import xarray as xr

from ops_qc.readers import MangopareStandardReader
from ops_qc.readers import MangopareMetadataReader
from ops_qc.apply_qc import QcApply
from ops_qc.preprocess import PreProcessMangopare

#ds = MagicMock()

class TestApplyQC(unittest.TestCase):

    def setUp(self):
        self.attr_file = 'tests/testdata/attribute_list.yml'
        self.test_list = ['impossible_date', 'impossible_location', 'impossible_speed','global_range', 'remove_ref_location', 'gear_type', 'spike', 'stuck_value', 'rate_of_change_test']
        filename = 'tests/testdata/MOANA_0038_13_210624041106.csv'
        metafile = 'tests/testdata/Trial_fisherman_database_tests.csv'
        ds = MangopareStandardReader(filename).run()
        metadata = MangopareMetadataReader(metafile).run()
        self.ds = PreProcessMangopare(ds,metadata,filename).run()

    def test_applyqc(self):
        ds = QcApply(self.ds,self.test_list,save_flags=True,attr_file=self.attr_file).run()
        assert isinstance(ds,xr.core.dataset.Dataset)
