import pandas as pd
import numpy as np
from datetime import datetime
#from global_land_mask import globe
import logging
from ops_qc.utils import calc_speed, point_on_land
import seawater as sw
import shapefile
from shapely.geometry import Point, shape
from shapely.ops import nearest_points


"""
QC Tests for ocean observations.  The test options are:
gear_type, timing_gap_test, impossible_date, impossible_location,
position_on_land, impossible_speed, global_range, climatology_test,
spike, stuck_value, rate_of_change_test, remove_ref_location.

Currently, some tests are not recommended or not complete:
timing_gap_test, position_on_land, climatology_test.

Tests that are particularly useful/necessary:
impossible_date, impossible_location, impossible_speed,
global_range, remove_ref_location

Possibly useful:
gear_type, spike, stuck_value, rate_of_change_test

Note these are constantly changing/being updated/improved.
"""

def gear_type(self, fail_flag=3, gear=None, flag_name = 'flag_gear_type'):
    try:
        if not gear:
            gear = self.ds.attrs['gear_class']
    except Exception as exc:
        self.logger.error('Could not determine gear type for gear_type qc test. Traceback: {}'.format(exc))

    self.qcdf[flag_name] = np.ones_like(self.df['DATETIME'], dtype='uint8')
    if "speed" not in self.df:
        self.df = calc_speed(self.df, units='kts')
    mean_speed = np.nanmean(self.df['speed'])
    if (mean_speed > 0 and gear == 'stationary') or (mean_speed == 0 and gear == 'mobile'):
        self.qcdf[flag_name] = fail_flag


# 4. Timing/gap test


def timing_gap_test(self, fail_flag=3, flag_name='flag_timing_gap'):
    """
    Take another look at this, do not include for now
    """
    self.qcdf[flag_name] = np.ones_like(self.df['DATETIME'], dtype='uint8')
    currdate = datetime.utcnow()
    tim_inc = 24  # hours
    time_gap = currdate - self.df['DATETIME'].iloc[-1]
    if time_gap.total_seconds() / 3600 > tim_inc:
        self.qcdf[flag_name] = fail_flag


# 5. Impossible date test

def impossible_date(self, min_date=datetime(2010, 1, 1), max_date = datetime.utcnow(), fail_flag=4, flag_name = 'flag_date'):
    """
    Makes sure observation data is within a specified valid range.
    Min_date here should really come from fishing metadata
    """
    self.qcdf[flag_name] = np.ones_like(self.df['DATETIME'], dtype='uint8')
    self.qcdf.loc[(self.df['DATETIME'] >= max_date), flag_name] = fail_flag
    # min date could be a spreadsheet error
    self.qcdf.loc[(self.df['DATETIME'] <= min_date), flag_name] = 3


# 6. Impossible location test

def impossible_location(self, lonrange=None, latrange=None, fail_flag=4, flag_name = 'flag_location'):
    """
    Check if lat,lon within  specified lat and lon ranges.
    Could actually be any two ranges...one day might update
    to be general and not just lat/lon.  Lonrange is [-180,360]
    to account for either -180 to 180 or 0 to 360.
    """
    if latrange is None:
        latrange = [-90, 90]
    if lonrange is None:
        lonrange = [-180, 360]
    self.qcdf[flag_name] = np.ones_like(self.df['LATITUDE'], dtype='uint8')
    self.qcdf.loc[((self.df['LATITUDE'] <= latrange[0]) | (self.df['LATITUDE'] >= latrange[1]) | (
            self.df['LONGITUDE'] <= lonrange[0]) | (
                             self.df['LONGITUDE'] >= lonrange[1])), flag_name] = fail_flag


# 7. Position on land test


def position_on_land_old(self, fail_flag=3):
    """
    Spatial resolution of globe.is_land is 1km.  Not sufficient,
    but need to think about how to efficientlly import higher res mask.
    Leaving this test out for now.
    """
    self.qcdf['flag_land'] = np.ones_like(self.df['LATITUDE'], dtype='uint8')
    self.qcdf.loc[(globe.is_land(self.df['LATITUDE'],
                                 self.df['LONGITUDE'])), 'flag_land'] = fail_flag

def position_on_land(self, fail_flag=3, flag_name = 'flag_land'):
    """
    Spatial resolution of globe.is_land is 1km.  Not sufficient,
    but need to think about how to efficientlly import higher res mask.
    Leaving this test out for now.
    """
    self.qcdf[flag_name] = np.ones_like(self.df['LATITUDE'], dtype='uint8')
    all_shapes = shapefile.Reader("/source/ops-qc/ops_qc/land_mask/ne_10m_land.shp").shapes()
    failed = []
    for lon,lat in zip(self.df['LONGITUDE'],self.df['LATITUDE']):
        lon = (lon+180)%360-180
        failed.append(point_on_land(point=(lon,lat),all_shapes=all_shapes,tol=200))
    self.qcdf.loc[failed, flag_name] = fail_flag

# 8. Impossible speed test

def impossible_speed(self, max_speed=100, fail_flag=4, flag_name = 'flag_speed'):
    """
    Don't really like calculating speed twice.  (Fixed)
    max_speed in knots
    """
    self.qcdf[flag_name] = np.ones_like(self.df['DATETIME'], dtype='uint8')
    #    self.df.reset_index(drop=True)  #not sure why this is here?
    if "speed" not in self.df:
        self.df = calc_speed(self.df, units='kts')
    if np.nanmean(np.absolute(self.df['speed'])) != 0:
        self.qcdf[flag_name] = 1
        self.qcdf.loc[(self.df['speed'] > max_speed), flag_name] = fail_flag

# 9. Global range test

def global_range(self, ranges=None, fail_flag=4):
    """
    Simplified version based on our experience so far.
    Applies as many ranges tests to as many variables as you'd like.
    """
    if ranges is None:
        ranges = {'PRESSURE': [0, 2000, 'flag_global_range_pres'], 'TEMPERATURE': [-2, 35, 'flag_global_range_temp']}
    for var, limit in ranges.items():
        flag_name = limit[2]
        limit = limit[0:2]
        self.qcdf[flag_name] = np.ones_like(self.df[var], dtype='uint8')
        self.qcdf.loc[(self.df[var] < limit[0]) | (self.df[var] > limit[1]), flag_name] = fail_flag

# 10. Climatology test

def climatology_test(self):
    """
    Not sure what this is doing that is different from global_range test.
    I think this should load a climatology dataset.
    We don't have a reliable enough one for NZ to apply this.
    Leaving out for now.
    """
    T_season_min = 0
    T_season_max = 25
    S_season_min = 0
    S_season_max = 50

    self.df['flag_clima'] = 1
    self.df.loc[((self.df['TEMPERATURE'] > T_season_max) | (
            self.df['TEMPERATURE'] < T_season_min)), 'flag_clima'] = 3

    if 'SALINITY' in self.df:
        self.df.loc[
            ((self.df['SALINITY'] > S_season_max) | (self.df['SALINITY'] < S_season_min)), 'flag_clima'] = 3


# 11. Spike test

def spike(self, qc_vars=None, fail_flag=4):
    """
    So far this has only removed good data...need really high
    thresholds. Because I think all of the spike section could
    be rethought and I'm not sure how it should be done yet.
    qc_vars maps variable to number of standard deviations to be
    the threshold
    """
    if qc_vars is None:
        qc_vars = {'TEMPERATURE': [3,'flag_spike_temp'], 'PRESSURE': [2,'flag_spike_pres']}
    for var, params in qc_vars.items():
        sdfactor = params[0]
        flag_name = params[1]
        self.qcdf[flag_name] = np.ones_like(self.df[var], dtype='uint8')
        thresh = np.std(self.df[var])*sdfactor
        val = np.abs(np.convolve(self.df[var], [-0.5, 1, -0.5], mode='same'))
        #val = np.hstack((0,val))[:-1]
        self.qcdf.loc[val > thresh, flag_name] = fail_flag

# 12. Stuck value test

def stuck_value(self, qc_vars=None, rep_num=5, fail_flag=2):
    """
    Adapted from QARTOD - sort of.  This whole thing is suspect as implemented
    here.  rep_num should be over a given amount of time, not number of obs.
    Maybe not that useful of a test, since with stationary gear, could stay the
    same.  Or write different thresholds for stationary vs mobile.
    """
    if qc_vars is None:
        qc_vars = {'TEMPERATURE': [.05,'flag_stuck_value_temp'], 'PRESSURE': [.01,'flag_stuck_value_pres']}
    if not isinstance(rep_num, int):
        raise TypeError("Maximum number of repeated values must be type int.")
    for var, params in qc_vars.items():
        thresh = params[0]
        flag_name = params[1]
        self.qcdf[flag_name] = np.ones_like(self.df[var], dtype='uint8')
        arr = self.df[var]
        it = np.nditer(arr)
        # Maybe not very efficient, based on QARTOD code
        for elem in it:
            idx = it.iterindex
            if idx >= rep_num:
                is_suspect = np.all(np.abs(arr[idx - rep_num: idx] - elem) < thresh)
                if is_suspect:
                    self.qcdf[flag_name].iloc[idx - rep_num: idx] = fail_flag


# 13. Rate of change test

def rate_of_change_test(self, thresh=2, fail_flag=3, varx='PRESSURE', vary='TEMPERATURE', flag_name = 'flag_roc'):
    """
    Thresh is in units of y/x, or temp (degC) per dbar.  Actual threshold
    is thresh + 2SD (standard deviation)
    first_thresh applies only to the first data point.  It's more strict
    because the first point is often bad due to adjustment from air temp.
    Old version doesn't really work for Mangopare, because the pressure
    delta isn't taken into consideration.  Another QARTOD-ish version:
    """
    y = self.df[vary]
    x = self.df[varx]
    try:
        sd = np.std(y)
        thresh = thresh + 2*sd
        self.qcdf[flag_name] = np.ones_like(x, dtype='uint8')
        # express rate of change as seconds, unit conversions will handle proper
        # comparison to threshold later
        with np.errstate(divide='ignore', invalid='ignore'):
            roc = np.abs(np.divide(np.diff(y), np.diff(x)))
        exceed = np.insert(roc > thresh, 0, False)
        self.qcdf[flag_name].loc[exceed] = fail_flag
    except Exception as exc:
        self.logger.error('Could not apply rate of change test: {}'. format(exc))


# 14.  Within radius of "bad" location (i.e. to remove calibration tests)

def remove_ref_location(self, bad_radius=5, ref_lat=-41.25707, ref_lon=173.28393, fail_flag=4, flag_name = 'flag_ref_loc'):
    """
    Defaults correspond to Zebra-Tech's location in Nelson, NZ
    in order to remove any testing values that weren't offloaded
    from the sensors at the time of test.
    """
    self.qcdf[flag_name] = np.ones_like(self.df['LATITUDE'], dtype='uint8')
    lats = self.df['LATITUDE']
    lons = self.df['LONGITUDE']
    d = [float(sw.dist([ref_lat, lat], [ref_lon, lon])[0]) for lat, lon in zip(lats, lons)]
    self.qcdf.loc[np.array(d) < bad_radius,flag_name] = fail_flag
