import unittest
import os
import pandas as pd
import xarray as xr

from ops_qc.readers import MangopareStandardReader
from ops_qc.readers import MangopareMetadataReader
from ops_qc.apply_qc import QcApply
from ops_qc.preprocess import PreProcessMangopare

#ds = MagicMock()

test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testdata')

class TestApplyQC(unittest.TestCase):

    def setUp(self):
        self.attr_file = os.path.join(test_dir, 'attribute_list.yml')
        self.test_list = ['impossible_date', 'impossible_location', 'impossible_speed','global_range', 'remove_ref_location', 'gear_type', 'spike', 'stuck_value', 'rate_of_change_test']
        test_filename = os.path.join(test_dir, 'MOANA_0038_13_210624041106.nc')
        self.ds = xr.open_dataset(test_filename)

    def test_applyqc(self):
        ds = QcApply(self.ds,self.test_list,save_flags=False,attr_file=self.attr_file).run()
        assert isinstance(ds,xr.core.dataset.Dataset)
