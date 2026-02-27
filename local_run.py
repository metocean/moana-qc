# docker run -ti --rm -v /config:/config -v /data:/data -v /archive:/archive -v /data_exchange:/data_exchange metocean/ops-qc:v0.6.0
from ops_qc import utils, wrapper
filelist=['/data/obs/mangopare/raw/MOANA_0874_88_250118050034.csv','/data/obs/mangopare/raw/MOANA_0874_89_250119165953.csv']
# filelist=['/data/obs/mangopare/raw/MOANA_0701_566_240502181509.csv', '/data/obs/mangopare/raw/MOANA_0364_95_240502192108.csv', '/data/obs/mangopare/raw/MOANA_0238_1203_240502205450.csv', '/data/obs/mangopare/raw/MOANA_0238_1200_240502164154.csv', '/data/obs/mangopare/raw/MOANA_0238_1201_240502181331.csv', '/data/obs/mangopare/raw/MOANA_0238_1202_240502201818.csv', '/data/obs/mangopare/raw/MOANA_0238_1199_240502154738.csv', '/data/obs/mangopare/raw/MOANA_0387_87_240502190041.csv', '/data/obs/mangopare/raw/MOANA_0301_542_240502201814.csv', '/data/obs/mangopare/raw/MOANA_0474_657_240502205000.csv', '/data/obs/mangopare/raw/MOANA_0452_633_240502180607.csv', '/data/obs/mangopare/raw/MOANA_0421_469_240502203736.csv', '/data/obs/mangopare/raw/MOANA_0421_468_240502192610.csv', '/data/obs/mangopare/raw/MOANA_0421_467_240502180414.csv', '/data/obs/mangopare/raw/MOANA_0337_461_240502205704.csv', '/data/obs/mangopare/raw/MOANA_0229_147_240502200721.csv', '/data/obs/mangopare/raw/MOANA_0020_2265_240502203659.csv']
gear_class={'Bottom trawl': 'mobile', 'Potting': 'stationary', 'Long lining': 'stationary', 'Trawling':'mobile','Midwater trawl': 'mobile','Purse seine netting': 'stationary', 'Bottom trawling': 'mobile','Research': 'mobile', 'Education': 'mobile', 'Bottom trawler': 'mobile', 'Bottom long line': 'stationary','waka':'mobile','Danish seining':'stationary','Netting':'stationary','Set netting':'stationary','Bottom long line':'stationary','Dredge':'mobile','Instrument deployment':'mobile','Diving':'stationary','Trolling':'mobile'}
out_dir = '/data/obs/mangopare/processed/'
outfile_ext = '_qc'
test_list_1 = ['impossible_date', 'impossible_location', 'impossible_speed', 'timing_gap',
'global_range', 'remove_ref_location', 'spike', 'temp_drift','stationary_position_check']
test_list_2 = ['start_end_dist_check']
wrapper.QcWrapper(filelist,outfile_ext,out_dir,test_list_1,test_list_2,gear_class=gear_class).run()

import glob
filelist= sorted(glob.glob('/data/obs/mangopare/processed/*.nc'))
#filelist= ['/data/obs/mangopare/processed/MOANA_0701_566_240502181509_qc.nc', '/data/obs/mangopare/processed/MOANA_0238_1203_240502205450_qc.nc', '/data/obs/mangopare/processed/MOANA_0238_1200_240502164154_qc.nc', '/data/obs/mangopare/processed/MOANA_0238_1201_240502181331_qc.nc', '/data/obs/mangopare/processed/MOANA_0238_1202_240502201818_qc.nc', '/data/obs/mangopare/processed/MOANA_0238_1199_240502154738_qc.nc', '/data/obs/mangopare/processed/MOANA_0301_542_240502201814_qc.nc', '/data/obs/mangopare/processed/MOANA_0474_657_240502205000_qc.nc', '/data/obs/mangopare/processed/MOANA_0452_633_240502180607_qc.nc', '/data/obs/mangopare/processed/MOANA_0421_469_240502203736_qc.nc', '/data/obs/mangopare/processed/MOANA_0421_468_240502192610_qc.nc', '/data/obs/mangopare/processed/MOANA_0421_467_240502180414_qc.nc', '/data/obs/mangopare/processed/MOANA_0337_461_240502205704_qc.nc', '/data/obs/mangopare/processed/MOANA_0229_147_240502200721_qc.nc', '/data/obs/mangopare/processed/MOANA_0020_2265_240502203659_qc.nc']
out_dir= '/data/obs/mangopare/GTS/test/'
GTS_template= 'GTS_encode_ship'
centre_code= 69
from GTS_encode.GTS_encode_wrapper import Wrapper
gts = Wrapper(filelist,
        out_dir,
        GTS_template,
        centre_code).run()

import glob
filelist = sorted(glob.glob('/data/obs/mangopare/GTS/test/*'))
from GTS_encode.transfer import dataserv
destination= 'metocean@dataserv2.hm:/hub/data/obs/GTS/'
dataserv(filelist, destination).run()