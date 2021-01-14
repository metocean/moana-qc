import qc_apply

test_list = ['impossible_date', 'impossible_location', 'impossible_speed',
'global_range', 'remove_ref_location']

test_list_2 = ['impossible_date', 'impossible_location', 'impossible_speed',
'global_range', 'remove_ref_location', 'gear_type', 'spike', 'stuck_value', 'rate_of_change_test']

ds2 = qc_apply.QcApply(ds1,test_list,save_flags=True).run()
