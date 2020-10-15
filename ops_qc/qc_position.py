import logging
import numpy as np
from scipy.signal import savgol_filter
import pandas as pd


'''  Methods relating to calculating fishing gear positions from vessel positions '''

def calc_stationary_loc(self,surface_depth = 5):
    try:
        ds[ds['lon']==0] = np.nan
        ds = ds.dropna()
        ds2 = ds[ds['depth']<surface_depth]
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
    ds = ds.dropna()
    ts = ds['time'].astype('datetime64[s]').astype('int64')/1e9
    ts = ts - ts[0]
    temp = ds['depth'] 
    tempfilt = savgol_filter(temp, window_length=9, polyorder=3) 

    dev1 = np.gradient(tempfilt,ts)
    cutoff = np.std(dev1)/2.5

    cat = np.array(["DEPL" for x in range(len(temp))])
    cat[dev1>cutoff] = "DESC"
    cat[-dev1>cutoff] = "ASCD"
    descend = dev1[dev1>cutoff]
    ascend = dev1[-dev1>cutoff]
    ds['Type'] = cat
    return ds