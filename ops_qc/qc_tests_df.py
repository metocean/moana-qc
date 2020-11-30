import pandas as pd
import numpy as np
from datetime import datetime
from global_land_mask import globe
import geopy.distance
import setup_rtd
import logging
from qc_utils import haversine, speed

############
#  QC TESTS
############

# 3. Gear type control.

def gear_type(self,fail_flag = 3):
    self.df['flag_gear_type'] = 1
    if not "speed" in self.df:
        self.df,mean_speed = calc_speed(self.df)
    if (mean_speed > 0 and gear == 'stationary') or (mean_speed == 0 and gear == 'mobile'):
        self.df['flag_gear_type'] = fail_flag

# 4. Timing/gap test

def timing_gap_test(self,fail_flag = 3):
    '''
    Take another look at this, do not include for now
    '''
    self.df['flag_timing_gap'] = 1
    currdate = datetime.utcnow()
    tim_inc = 24  # hours
    time_gap = currdate - self.df['DATETIME'].iloc[-1]
    if time_gap.total_seconds()/3600 > tim_inc:
        self.df['flag_timing_gap'] = fail_flag


# 5. Impossible date test

def impossible_date(self,min_date = datetime(2010, 1, 1),fail_flag = 4):
    '''
    Min_date here should really come from fishing metadata
    '''
    self.df['flag_date'] = 1
    currdate = datetime.now()
    self.df.loc[((self.df['DATETIME'] >= currdate)), 'flag_date'] = fail_flag
    # min date could be a spreadsheet error
    self.df.loc[((self.df['DATETIME'] <= mindate)), 'flag_date'] = 3


# 6. Impossible location test

def impossible_location(self,lonrange = [-180, 360], latrange = [-90, 90], fail_flag = 4):
    self.df['flag_location'] = 1
    self.df.loc[((self.df['LATITUDE'] <= latrange[0]) | (self.df['LATITUDE'] >= latrange[1]) | (self.df['LONGITUDE'] <= lonrange[0]) | (self.df['LONGITUDE'] >= lonrange[1])), 'flag_location'] = fail_flag

# 7. Position on land test

def position_on_land(self, fail_flag = 3):
    '''
    Spatial resolution of globe.is_land is 1km.  Not sufficient,
    but need to think about how to efficientlly import higher res mask.
    Leaving this test out for now.
    '''
    self.df['flag_land'] = 1
    self.df.loc[(globe.is_land(self.df['LATITUDE'], self.df['LONGITUDE'])), 'flag_land'] = fail_flag


# 8. Impossible speed test

def impossible_speed(self,max_speed = 100, fail_flag = 4):
    '''
    Don't really like calculating speed twice.  (Fixed)
    max_speed in knots
    '''
    self.df['flag_speed'] = 1
#    self.df.reset_index(drop=True)  #not sure why this is here?
    if not "speed" in self.df:
        self.df = calc_speed(self.df,units='kts')
    if np.nanmean(np.absolute(df['speed']))!= 0:
        self.df['flag_speed'] = 1
        self.df.loc[(self.df['speed'] > max_speed), 'flag_speed'] = fail_flag
    self.df = self.df.drop(columns=['speed'])


# 9. Global range test

def global_range(self, ranges = {'PRESSURE':[0,10000],'TEMPERATURE':[-2,50]}, fail_flag = 4):
    '''
    Simplified version based on our experience so far.
    Applies as many ranges tests to as many variables as you'd like.
    '''
    self.df['flag_global_range'] = 1
    for var,limit in ranges:
        self.df.loc[(self.df[var] < limit[0]) | (self.df[var] > limit[1])), 'flag_global_range'] = fail_flag

# 10. Climatology test

def climatology_test(self):
    '''
    Not sure what this is doing that is different from global_range test.
    I think this should load a climatology dataset.
    We don't have a reliable enough one for NZ to apply this.
    Leaving out for now.
    '''
    T_season_min = 0
    T_season_max = 25
    S_season_min = 0
    S_season_max = 50

    self.df['flag_clima'] = 1
    self.df.loc[((self.df['TEMPERATURE'] > T_season_max) | (self.df['TEMPERATURE'] < T_season_min)), 'flag_clima'] = 3

    if 'SALINITY' in self.df:
        self.df.loc[
            ((self.df['SALINITY'] > S_season_max) | (self.df['SALINITY'] < S_season_min)), 'flag_clima'] = 3


# 11. Spike test

def spike(self, vars = {'TEMPERATURE':10,'PRESSURE':100}, fail_flag = 4):
    '''
    So far this has only removed good data...need really high
    thresholds. Because I think all of the spike section could
    be rethought and I'm not sure how it should be done yet.
    '''
    self.df['flag_temp_spike'] = 1
    for var, thresh in vars:
        val = np.abs(np.convolve(self.df[var], [-0.5, 1, -0.5], mode='same'))
        val[[0, -1]] = 0
        self.df.loc[val > thresh, 'flag_temp_spike'] = fail_flag

# 12. Stuck value test

def stuck_value(self,vars = {'TEMPERATURE':.005,'PRESSURE':.01},rep_num = 5, fail_flag = 3):
    '''
    Adapted from QARTOD - sort of.  This whole thing is suspect as implemented
    here.
    '''
    self.df['flag_temp_stuck'] = 1
    if not isinstance(rep_num, int):
        raise TypeError("Maximum number of repeated values must be type int.")
    for var,thresh in vars:
        arr = self.df[var]
        it = np.nditer(arr)
        # Maybe not very efficient, based on QARTOD code
        for elem in it:
            idx = it.iterindex
            if idx >= rep_num:
                is_suspect = np.all(np.abs(arr[idx - rep_num:idx] - elem) < thresh)
                if is_suspect:
                    self.df['flag_temp_stuck'].iloc[idx] = fail_flag

# 13. Rate of change test

def rate_of_change_test(self):
    '''
    Old version doesn't really work for Mangopare, because the time
    delta isn't taken into consideration.
    '''
    self.df['flag_RoC'] = 1

    sd_temp_prof = self.df[self.df['type'] == 'PROF']['TEMPERATURE'].std()
    sd_temp_bottom = self.df[self.df['type'] == 3]['TEMPERATURE'].std()

    n_dev = 3 # threshold

    self.df['prev_temp'] = self.df['TEMPERATURE'].shift(1)

    self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_down)), 'flag_RoC'] = 3
    self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_bottom)), 'flag_RoC'] = 3
    self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_up)), 'flag_RoC'] = 3

    self.df = self.df.drop(columns=['prev_temp'])

# 14.  Within radius of "bad" location (i.e. to remove calibration tests)
