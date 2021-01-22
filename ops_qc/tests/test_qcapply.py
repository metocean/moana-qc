import qc_apply


test_list = ['impossible_date', 'impossible_location', 'impossible_speed',
'global_range', 'remove_ref_location', 'gear_type', 'spike', 'stuck_value', 'rate_of_change_test']

import unittest
import qc_tests_df as qc_tests
from ops_qc.apply_qc import QcApply

ds = MagicMock()

qcapply = QcApply(ds = ds,
                 test_list=None,
                 save_flags=False,
                 convert_p_to_z=True,
                 default_latitude=-40,
                 attr_file='attribute_list.yml',
                 logger=logging)


class QcTestsTestCase(unittest.TestCase):

    def test_if_qctest_exists(self,test_list):
       """
       Check if all tests in test_list are
       available in qc_tests_df.py
       """
       for test_name in test_list:
           try:
               qc_test = getattr(qc_tests,test_name)
               qc_test(self)
               success_tests.append(test_name)
           except Exception as exc:
               tests_not_applied.append(test_name)
       self.assertEqual(sucess_tests, test_list)

#    def test_global_qc_flag(self):
#        qcapply._global_qc_flag
