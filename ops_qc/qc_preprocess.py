import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
import logging
import seawater as sw
from scipy.signal import savgol_filter
from qc_utils import catch
import qc_readers
from ops_core.utils import import_pycallable, catch_exception


############
#  QC PROCESSING APPLIED TO XARRAY DS
############
class PreProcessMangopare(object):
    '''
    Mangopare position processing and fishing gear classification.
    Inputs:
        ds: xarray dataset including data to be QC'd
        metadata: pandas dataframe with Mangopare fisher metadata
        These are generated using qc_readers.py, see for defaults.
    '''

    def __init__(self,
                ds,
                metadata,
                surface_pressure = 5,
                logger = logging):

        self.ds = ds
        self.fisher_metadata = fisher_metadata
        self.test_list = test_list
        self.test_order = test_order
        self.surface_pressure = surface_pressure
        self.logger = logging
        self.filename = self.ds.attrs['Raw data filename'].values

    def classify_gear (self):
        '''
        Takes fisher metadata spreadsheet info and matches it with the file being
        processed.
        Inputs include self.fisher_metadata from qc_readers.load_fisher_metadata and
        self.df from qc_readers.load_moana_standard/
        '''

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
            self.logger.error('Multiple entries found for this SN and time range in fisher metadata, skipping {}.'.format(self.filename))


    def calc_stationary_loc(self):
        '''
        Calculate locations for either stationary or mobile gear.
        Current state of this code assumes all stationary locations
        in one CSV file are the SAME.  NOT NECESSARILY TRUE!  Hence
        the commented out regions...eventually will use those.
        '''
        try:
            self.ds[self.ds['LONGITUDE']==0] = np.nan
            self.ds = self.ds.dropna()
            ds2 = self.ds[self.ds['PRESSURE']<self.surface_pressure]
            #if len(ds2.lat.values)==[1,2]:
            lat = np.nanmean(ds2.lat.values)
            lon = np.nanmean(ds2.lon.values)
            #else:
                # haven't worked out yet what to do if there's
                # lots of "surface" lat/lon pairs...that will go here:
                #lat = np.array(ds2.lat.values)
                #lon = np.array(ds2.lon.values)
            lon = [l%360 for l in lon]
        except:
            print("Position could not be calculated for {}".format(self.filename))

    def find_bottom(self, cutoff = False):
        '''
        Uses gradient to assign descending (DESC), ascending (ASC), or deployed (DEPL) status
        to each datapoint in fishing gear deployment.  Used to estimate average bottom or fishing
        temperature.
        '''
        try:
            self.ds = self.ds.dropna()
            ts = self.ds['time'].astype('datetime64[s]').astype('int64')/1e9
            ts = ts - ts[0]
            temp = self.ds['depth']
            tempfilt = savgol_filter(temp, window_length=9, polyorder=3)
            dev1 = np.gradient(tempfilt,ts)
        except exception as exc:
            cat = np.array(['NA' for x in range(len(temp))])
            self.logger.error('Filter or pressure gradient failed for {}.  NA applied instead.'.format(self.filename))
        try:
            if not cutoff:
                cutoff = np.std(dev1)/2.5
            cat = np.array(["DEPL" for x in range(len(temp))])
            cat[dev1>cutoff] = "DESC"
            cat[-dev1>cutoff] = "ASCD"
        except:
            cat = np.array(['NA' for x in range(len(temp))])
            self.logger.error('Gradient cutoff not applied to {}, NA applied instead.'.format(self.filename))
        self.ds['Phase'] = cat
        self.ds.Phase.attrs['Units'] = 'none'


    def run(self):
        self.classify_gear()
        if self.ds.attrs['Gear Class'] = 'stationary':
            self.calc_stationary_loc()
        self.find_bottom()
        return(self.ds)
