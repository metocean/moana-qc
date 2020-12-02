import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
import logging
import seawater as sw
from qc_utils import catch
import qc_readers
#from ops_core.utils import import_pycallable, catch_exception

var_attr_info = {
    'DATETIME':['time','datetime'],
    'LATITUDE':['latitude','degree_north'],
    'LONGITUDE':['longitude','degree_east'],
    'TEMPERATURE':['sea_water_temperature','degree_C'],
    'PRESSURE':['sea_water_pressure','dbar'],
    'PHASE':{'fishing_deployment_phase','na'}
    }

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
                fisher_metadata,
                surface_pressure = 5,
                logger = logging):

        self.ds = ds
        self.fisher_metadata = fisher_metadata
        self.surface_pressure = surface_pressure
        self.logger = logging
        self.filename = self.ds.attrs['Raw data filename']

    def _classify_gear (self):
        '''
        Takes fisher metadata spreadsheet info and matches it with the file being
        processed.
        Inputs include self.fisher_metadata from qc_readers.load_fisher_metadata and
        self.df from qc_readers.load_moana_standard/
        '''
        try:
            ms = int(self.ds.attrs['Moana Serial Number'])
            sn_data = self.fisher_metadata.loc[self.fisher_metadata['Mangopare serial number'] == ms]
            tmin = pd.to_datetime(np.min(self.ds['DATETIME']).values)
            tmax = pd.to_datetime(np.max(self.ds['DATETIME']).values)
            time_check = 0
            for idx,row in sn_data.iterrows():
                if tmin>=row['Date supplied'] and tmax<=row['Date returned']:
                    self.ds.attrs['Gear Class'] = row['Gear Class']
                    time_check+=1
            if time_check<1:
                self.logger.error('No valid time range found in fisher metadata.')
            if time_check>1:
                self.logger.error('Multiple entries found for this SN and time range in fisher metadata, skipping {}.'.format(self.filename))
        except:
            self.ds.attrs['Gear Class'] = 'unknown'
            print('Gear Class calculation failed, labeled as unknown.')

    def _calc_positions(self,surface_pressure = 5):
        '''
        Calculate locations for either stationary or mobile gear.
        Current state of this code assumes all stationary locations
        in one CSV file are the SAME.  NOT NECESSARILY TRUE!  Hence
        the commented out regions...eventually will use those.
        '''
        try:
            if self.ds.attrs['Gear Class'] == 'stationary':
                # Remove rows with nan lat/lon, which we kept in reader
                self.ds = self.ds.dropna(how='any',dim='DATETIME')
                # use self.surface_pressure if it exists
                try:
                    surface_pressure = self.surface_pressure
                except:
                    pass
                # Find when gear comes to/near the surface
                ds2 = self.ds.where(self.ds['PRESSURE']<surface_pressure,drop=True)
                #if len(ds2.lat.values)==[1,2]:
                lat = np.nanmean(ds2.LATITUDE.values)
                lon = np.nanmean(ds2.LONGITUDE.values)
                #else:
                    # haven't worked out yet what to do if there's
                    # lots of "surface" lat/lon pairs...that will go here:
                    #lat = np.array(ds2.lat.values)
                    #lon = np.array(ds2.lon.values)
                lons = np.ones_like(self.ds['LONGITUDE'])*lon
                lats = np.ones_like(self.ds['LATITUDE'])*lat
                self.ds['LATITUDE'] = xr.DataArray(lats,dims=['DATETIME'])
            if self.ds.attrs['Gear Class'] == 'mobile':
                lons = self.ds['LONGITUDE']
            # convert to 0-360 for both stationary and mobile gear:
            lons = [l%360 for l in lons]
            self.ds['LONGITUDE'] = xr.DataArray(lons,dims=['DATETIME'])
        except:
            print("Position could not be calculated for {}".format(self.filename))

    def _find_bottom(self, cutoff = '4 minutes'):
        '''
        Uses timedelta to assign profile (PROF) or deployed (DEPL) status
        to each datapoint in fishing gear deployment.  Used to estimate average bottom or fishing
        temperature.
        Currently a big mess.  But xarray was being annoying and I don't
        know why I can't figure out how to subtract two times to get a
        datetime timedelta NOT an int!!!
        '''
        try:
            cutoff = pd.Timedelta(cutoff)
            df = self.ds.to_dataframe()
            df.reset_index(inplace=True)
            times = df['DATETIME']
            t_delta = (times-times.shift()).fillna(pd.Timedelta('0 days'))
            cat = np.full_like(self.ds['TEMPERATURE'],'DEPL',dtype='S4')
            cat[t_delta<cutoff] = "PROF"
        except:
            cat = np.full_like(self.ds['TEMPERATURE'],np.nan,dtype='float')
            self.logger.error('Bottom not found for {}, np.nan applied instead.'.format(self.filename))

        self.ds['PHASE'] = xr.Variable(dims ='DATETIME', data = cat)

    def _add_variable_attrs(self):
        '''
        Uses the local variable dictionary at the start of this file
        to specify the name and units for each var.
        Example dictionary: var_attr_info = {'LATITUDE':['latitude','units']}
        '''
        for var,[standard_name,units] in var_attr_info.items():
            self.ds[var].attrs.update({'standard_name': standard_name,
                                        'units':units})

    def run(self):
        self._classify_gear()
        self._calc_positions()
        self._find_bottom()
        self._add_variable_attrs()
        return(self.ds)
