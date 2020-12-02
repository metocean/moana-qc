import ..qc_readers
import ..qc_preprocess
from importlib import reload

def test_mangopare_reader():
    # for mobile gear:
    filename = '/Users/jjakoboski/Desktop/MetOcean/MOANA_0028_15_201128004121.csv'
    filename = '/Users/jjakoboski/Desktop/MetOcean/MOANA_0026_30_201106230019.csv'

    # for stationary gear:
    metafile = '/Users/jjakoboski/Desktop/MetOcean/Trial_fisherman_database.csv'

    ds = qc_readers.MangopareStandardReader(filename).run()
    metadata = qc_readers.MangopareMetadataReader(metafile).run()
    return(ds,metadata)
