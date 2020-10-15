import pandas as pd
import numpy as np
from datetime import datetime
from global_land_mask import globe
import geopy.distance
import setup_rtd
import logging

#######################################################################################################################
# QC
#######################################################################################################################

class QC_apply(object):
    '''Base class for observational data quality control.   
    Input dataframe with LONGITUDE, LATITUDE, DATETIME, PRESSURE, TEMPERATURE 
    of same shape and applies QC, designed for instruments mounted on fishing gear.
    Options for test_list: LIST ALL TESTS HERE
    '''
    def __init__(self, 
                ds = ds, 
                test_list = None, 
                save_flags = False,
                convert_p_to_z = True,
                logger = logging):

        self.ds = ds
        self.test_list = test_list
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.logger = logging
        self.df = self.ds.to_dataframe()
    
    def run(self):
        if test_list is not None:
            self.flag = np.ones_like(df['LONGITUDE'])
            run_tests()
        else:
            self.flag = np.zeros_like(df['LONGITUDE'])
        if convert_p_to_z:
            convert_to_depth()


    ############
    #  QC TESTS
    ############

    # 1. Platform identification, from line 93 load_cloud.py

    # 3. Gear type control.

    def gear_type(self, gear):
        # gt = 0 = fixed
        # gt = 1 = mobile
        self.df['flag_gear_type'] = 1
        self.df['speed'] = 0
        if len(self.df) != 0:
            for i in self.df.iloc[:-1].index:
                time1 = self.df.DATETIME.iloc[i]
                time2 = self.df.DATETIME.iloc[i + 1]
                coords_1 = self.df.LATITUDE.iloc[i], self.df.LONGITUDE.iloc[i]
                coords_2 = self.df.LATITUDE.iloc[i + 1], self.df.LONGITUDE.iloc[i + 1]
                d = geopy.distance.geodesic(coords_1, coords_2).m
                t = (time2 - time1).seconds
                self.df['speed'].iloc[i] = d / t if t != 0 else None
        speed = self.df['speed'].mean()
        self.df = self.df.drop(columns=['speed'])

        gt = 0 if speed == 0 else 1

        if (gt == 1 and gear == 'Fixed') or (gt == 0 and gear == 'Mobile'):
            self.df['flag_gear_type'] = 3
        
        self.flag[self.flag<self.df['flag_gear_type']] = self.df['flag_gear_type']

    # 4. Timing/gap test

    def timing_gap_test(self):
        self.df['flag_timing_gap'] = 1
        currdate = datetime.utcnow()
        tim_inc = 24  # hours
        time_gap = currdate - self.df['DATETIME'].iloc[-1]
        if time_gap.total_seconds()/3600 > tim_inc:
            self.df['flag_timing_gap'] = 3


    # 5. Impossible date test

    def impossible_date(self):
        self.df['flag_date'] = 1
        currdate = datetime.now()
        mindate = datetime(2010, 1, 1)
        self.df.loc[((self.df['DATETIME'] > currdate) | (self.df['DATETIME'] < mindate)), 'flag_date'] = 4


    # 6. Impossible location test

    def impossible_location(self):
        self.df['flag_location'] = 1
        latrange = [-90, 90]
        lonrange = [-180, 180]
        self.df.loc[((self.df['LATITUDE'] < latrange[0]) | (self.df['LATITUDE'] > latrange[1]) | (self.df['LONGITUDE'] < lonrange[0]) | (self.df['LONGITUDE'] > lonrange[1])), 'flag_location'] = 4


    # 7. Position on land test

    def position_on_land(self):
        self.df['flag_land'] = 1
        self.df.loc[(globe.is_land(self.df['LATITUDE'], self.df['LONGITUDE'])), 'flag_land'] = 4


    # 8. Impossible speed test

    def impossible_speed(self):
        self.df['flag_speed'] = 1
        self.df['speed'] = 0
        self.df.reset_index(drop=True)
        if len(self.df) != 0:
            for i in self.df.iloc[:-1].index:
                time1 = self.df.DATETIME.iloc[i]
                time2 = self.df.DATETIME.iloc[i+1]
                coords_1 = self.df.LATITUDE.iloc[i], self.df.LONGITUDE.iloc[i]
                coords_2 = self.df.LATITUDE.iloc[i+1], self.df.LONGITUDE.iloc[i+1]
                d = geopy.distance.geodesic(coords_1, coords_2).m
                t = (time2 - time1).seconds
                self.df['speed'].iloc[i] = d/t if t != 0 else None
            if self.df['speed'].mean() != 0:
                self.df['flag_speed'] = 1
                self.df.loc[(self.df['speed'] > 4.12), 'flag_speed'] = 4
            self.df = self.df.drop(columns=['speed'])


    # 9. Global range test

    def global_range(self):
        self.df['flag_global_range'] = 1
        self.df.loc[(self.df['PRESSURE'] >= -5) & (self.df['PRESSURE'] < 0), 'flag_global_range'] = 3
        self.df.loc[(self.df['PRESSURE'] < -5), 'flag_global_range'] = 4
        self.df.loc[((self.df['TEMPERATURE'] < -2) | (self.df['TEMPERATURE'] > 35)), 'flag_global_range'] = 4
        if 'SALINITY' in self.df:
            self.df.loc[((self.df['SALINITY'] < 2) | (self.df['SALINITY'] > 42)), 'flag_global_range'] = 4


    # 10. Climatology test

    def climatology_test(self):
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

    def spike(self):
        self.df['flag_temp_spike'] = 1
        self.df['prev_temp'] = self.df['TEMPERATURE'].shift(1)
        self.df['post_temp'] = self.df['TEMPERATURE'].shift(-1)
        self.df['val'] = abs(self.df.TEMPERATURE - (self.df.post_temp + self.df.prev_temp) / 2) - abs((self.df.post_temp - self.df.prev_temp) / 2)
        self.df.loc[(((self.df['PRESSURE'] < 500) & (self.df['val'] > 6)) | ((self.df['PRESSURE'] >= 500) & (self.df['val'] > 2))), 'flag_temp_spike'] = 4
        self.df = self.df.drop(columns=['prev_temp', 'post_temp', 'val'])

        if 'SALINITY' in self.df:
            self.df['flag_sal_spike'] = 1
            self.df['prev_sal'] = self.df['SALINITY'].shift(1)
            self.df['post_sal'] = self.df['SALINITY'].shift(-1)
            self.df['val'] = abs(self.df.SALINITY - (self.df.post_sal + self.df.prev_sal) / 2) - abs(
                (self.df.post_sal - self.df.prev_sal) / 2)
            self.df.loc[(((self.df['PRESSURE'] < 500) & (self.df['val'] > 0.9)) | (
                        (self.df['PRESSURE'] >= 500) & (self.df['val'] > 0.3))), 'flag_sal_spike'] = 4
            self.df = self.df.drop(columns=['prev_sal', 'post_sal', 'val'])


    # 12. Stuck value test

    def stuck(self):
        self.df['flag_temp_stuck'] = 1
        self.df['prev_temp_1'] = self.df['TEMPERATURE'].shift(1)
        self.df['prev_temp_2'] = self.df['TEMPERATURE'].shift(2)
        self.df['post_temp_1'] = self.df['TEMPERATURE'].shift(-1)
        self.df['post_temp_2'] = self.df['TEMPERATURE'].shift(-2)
        self.parse_segments()
        self.df.loc[((self.df['prev_temp_1'] == self.df['TEMPERATURE']) & (self.df['post_temp_1'] == self.df['TEMPERATURE']) & (self.df['type'] != 3)), 'flag_temp_stuck'] = 3
        self.df.loc[((self.df['prev_temp_1'] == self.df['TEMPERATURE']) & (
                self.df['post_temp_1'] == self.df['TEMPERATURE']) & (
                                 self.df['prev_temp_2'] == self.df['TEMPERATURE']) & (
                             self.df['post_temp_2'] == self.df['TEMPERATURE']) & (self.df['type'] != 3)), 'flag_temp_stuck'] = 4
        self.df = self.df.drop(columns=['prev_temp_1', 'post_temp_1', 'prev_temp_2', 'post_temp_2'])

        if 'SALILNITY' in self.df:
            self.df['flag_sal_stuck'] = 1
            self.df['prev_sal_1'] = self.df['SALINITY'].shift(1)
            self.df['prev_sal_2'] = self.df['SALINITY'].shift(2)
            self.df['post_sal_1'] = self.df['SALINITY'].shift(-1)
            self.df['post_sal_2'] = self.df['SALINITY'].shift(-2)
            self.df.loc[((self.df['prev_sal_1'] == self.df['SALINITY']) & (self.df['post_sal_1'] == self.df['SALINITY']) & (
                        self.df['type'] != 3)), 'flag_sal_stuck'] = 3
            self.df.loc[((self.df['prev_sal_1'] == self.df['SALINITY']) & (
                    self.df['post_sal_1'] == self.df['SALINITY']) & (self.df['prev_sal_2'] == self.df['SALINITY']) & (
                                 self.df['post_sal_2'] == self.df['SALINITY']) & (
                        self.df['type'] != 3)), 'flag_sal_stuck'] = 4
            self.df = self.df.drop(columns=['prev_sal_1', 'post_sal_1', 'prev_sal_2', 'post_sal_2'])

        self.df = self.df.drop(columns=['vel', 'vel_smooth', 'delta_time', 'type'])


    # 13. Rate of change test

    def rate_of_change_test(self):
        self.df['flag_RoC'] = 1
        self.parse_segments()

        sd_temp_down = self.df[self.df['type'] == 2]['TEMPERATURE'].std()
        sd_temp_bottom = self.df[self.df['type'] == 3]['TEMPERATURE'].std()
        sd_temp_up = self.df[self.df['type'] == 1]['TEMPERATURE'].std()

        n_dev = 3 # threshold

        self.df['prev_temp'] = self.df['TEMPERATURE'].shift(1)

        self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_down)), 'flag_RoC'] = 3
        self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_bottom)), 'flag_RoC'] = 3
        self.df.loc[(abs(self.df['TEMPERATURE'] - self.df['prev_temp']) > (n_dev * sd_temp_up)), 'flag_RoC'] = 3

        if 'SALINITY' in self.df:
            sd_sal_down = self.df[self.df['type'] == 2]['SALINITY'].std()
            sd_sal_bottom = self.df[self.df['type'] == 3]['SALINITY'].std()
            sd_sal_up = self.df[self.df['type'] == 1]['SALINITY'].std()

            n_dev = 3  # threshold

            self.df['prev_sal'] = self.df['SALINITY'].shift(1)

            self.df.loc[(abs(self.df['SALINITY'] - self.df['prev_sal']) > (n_dev * sd_sal_down)), 'flag_RoC'] = 3
            self.df.loc[(abs(self.df['SALINITY'] - self.df['prev_sal']) > (n_dev * sd_sal_bottom)), 'flag_RoC'] = 3
            self.df.loc[(abs(self.df['SALINITY'] - self.df['prev_sal']) > (n_dev * sd_sal_up)), 'flag_RoC'] = 3

            self.df = self.df.drop(columns=['prev_sal'])

        self.df = self.df.drop(columns=['prev_temp'])


    def apply_segment_type_limits(self, row):
        if row['vel_smooth'] < -setup_rtd.parameters['segment_type_limit']:
            return 1
        elif row['vel_smooth'] > setup_rtd.parameters['segment_type_limit']:
            return 2
        else:
            return 3

    def parse_segments(self):
        # determine point descent velocity
        self.df['delta_time'] = self.df['DATETIME'].diff(periods=-1) / pd.offsets.Second(1)
        self.df['vel'] = self.df['PRESSURE'].diff(periods=-1) / self.df['delta_time'] * 1000
        self.df['vel_smooth'] = self.df['vel'].rolling(setup_rtd.parameters['rolling'], center=True,
                                                                   min_periods=1).mean()
        self.df['type'] = self.df.apply(lambda row: self.apply_segment_type_limits(row), axis=1)

        # create segments
        previous_segment_type = False
        previous_saved_segment_type = False
        segment_start_index = 0
        previous_saved_start_index = 0
        for index, row in self.df.iterrows():
            current_segment_type = row['type']
            if (current_segment_type != previous_segment_type and index != 0) or index == self.df.shape[0] - 1:
                segment_end_index = index if index == self.df.shape[0] - 1 else index - 1
                segment_size = segment_end_index - segment_start_index
                if segment_size > setup_rtd.parameters['segment_size']:
                    if previous_saved_segment_type == previous_segment_type:
                        segment_start_index = previous_saved_start_index
                    self.df.loc[segment_start_index:segment_end_index, 'type'] = previous_segment_type

                    previous_saved_segment_type = previous_segment_type
                    previous_saved_start_index = segment_start_index

                    segment_start_index = index

            previous_segment_type = current_segment_type


    ############
    #  ADDITIONAL PROCESSING FUNCTIONS
    ############

    def convert_to_depth(self):
        self.df['DEPTH'] = [sw.eos80.dpth(catch(lambda: float(p)),df['LATITUDE'].mean()) for p in df['PRESSURE']]

    def catch(func, handle=lambda e : e, *args, **kwargs):
    ''' Values that return an error are overwritten as np.nan...we just ignore them for now '''
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return np.nan

    ############
    #  POSITION RELATED METHODS
    ############

    def calc_stationary_loc(self,surface_depth = 5):
        '''
        Calculate locations for either stationary or mobile gear
        '''
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