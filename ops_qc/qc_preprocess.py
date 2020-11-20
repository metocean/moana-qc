import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
import logging
import seawater as sw
from scipy.signal import savgol_filter
from qc_utils import catch
import qc_readers

############
#  QC PROCESSING APPLIED TO XARRAY DS
############
class PreProcessMangopare(object):
    '''Deals with position processing and gear classification
    '''
    def __init__(self, 
                ds,
                metareader = qc_readers.MangopareMetadataReader,
                metafile = '/data/obs/mangopare/Trial_fishermen_database.csv',
                test_list = None,
                test_order = False,
                surface_pressure = 5,
                logger = logging):

        self.ds = ds
        self.metareader = metareader
        self.metafile = metafile
        self.test_list = test_list
        self.test_order = test_order
        self.surface_pressure = surface_pressure
        self.logger = logging

    def classify_gear (self,filename):
        '''
        Takes fisher metadata spreadsheet info and matches it with the file being
        processed.  
        Inputs include self.fisher_metadata from qc_readers.load_fisher_metadata and 
        self.df from qc_readers.load_moana_standard/
        '''
        self.fisher_metadata = self.metareader(metafile = self.metafile).run()

        ms = int(self.ds.attrs['Moana Serial Number'])
        sn_data = self.fisher_metadata.loc[self.fisher_metadata['Mangopare serial number'] == ms]
        tmin = pd.to_datetime(np.min(self.ds['DATETIME']).values)
        tmax = pd.to_datetime(np.max(self.ds['DATETIME']).values)
        time_check = 0
        for row in sn_data.iterrows():
            if tmin>=row['Date supplied'] and tmax<=row['Date returned']:
                self.ds.attrs['Gear Class'] = row['Gear Class']
                time_check+=1
        if time_check<1:
            self.logger.error('No valid time range found in fisher metadata.')
        if time_check>1:
            self.logger.error('Multiple entries found for this SN and time range in fisher metadata, skipping {}.'.format(filename))


    def calc_stationary_loc(self):
        '''
        Calculate locations for either stationary or mobile gear
        '''
        try:
            ds[ds['LONGITUDE']==0] = np.nan
            ds = ds.dropna()
            ds2 = ds[ds['PRESSURE']<surface_pressure]
            if len(ds2.lat.values)==[1,2]:
                lat = np.nanmean(ds2.lat.values)
                lon = np.nanmean(ds2.lon.values)
            else:
                lat = np.array(ds2.lat.values)
                lon = np.array(ds2.lon.values)
            lon = [l%360 for l in lon]
            return lat,lon
        except:
            print("Position could not be calculated.")

    def find_bottom(self, cutoff = 1):
        ''' 
        Uses gradient to assign descending (DESC), ascending (ASC), or deployed (DEPL) status
        to each datapoint in fishing gear deployment.  Used to estimate average bottom or fishing
        temperature.
        '''
        self.ds = self.ds.dropna()
        ts = self.ds['time'].astype('datetime64[s]').astype('int64')/1e9
        ts = ts - ts[0]
        temp = self.ds['depth'] 
        tempfilt = savgol_filter(temp, window_length=9, polyorder=3) 

        dev1 = np.gradient(tempfilt,ts)
        cutoff = np.std(dev1)/2.5

        cat = np.array(["DEPL" for x in range(len(temp))])
        cat[dev1>cutoff] = "DESC"
        cat[-dev1>cutoff] = "ASCD"
        self.ds['Phase'] = cat
        self.ds.Phase.attrs['Units'] = 'none'

    def run(self):

        return(self.ds)


