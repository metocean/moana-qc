from ops_qc.qc_readers import qc_readers
from .. import qc_preprocess
from importlib import reload

def test_mangopare_reader():
    # for mobile gear:
    filename = '/Users/jjakoboski/Desktop/MetOcean/MOANA_0028_15_201128004121.csv'
    filename = '/Users/jjakoboski/Desktop/MetOcean/MOANA_0026_30_201106230019.csv'

    filename = '/data/obs/mangopare/incoming/0028/MOANA_0028_15_201128004121.csv'
    filename = '/data/obs/mangopare/incoming/0026/MOANA_0026_30_201106230019.csv'


    # for stationary gear:
    metafile = '/Users/jjakoboski/Desktop/MetOcean/Trial_fisherman_database.csv'
    metafile = '/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv'

    ds = qc_readers.MangopareStandardReader(filename).run()
    metadata = qc_readers.MangopareMetadataReader(metafile).run()
    ds1 = qc_preprocess.PreProcessMangopare(ds,metadata).run()
    return(ds1,metadata)


filename = '/data/obs/mangopare/incoming/0026/MOANA_0026_30_201106230019.csv'
metafile = '/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv'
import qc_readers
import qc_preprocess
import qc_apply
ds = qc_readers.MangopareStandardReader(filename).run()
metadata = qc_readers.MangopareMetadataReader(metafile).run()
ds1 = qc_preprocess.PreProcessMangopare(ds,metadata).run()
test_list = ['impossible_date', 'impossible_location', 'impossible_speed',
'global_range', 'remove_ref_location', 'gear_type', 'spike']
ds2 = qc_apply.QcApply(ds1,test_list,save_flags=True).run()

