import numpy as np
import yaml
import datetime as dt
import glob
import os
from shapely.geometry import Point, shape
from shapely.ops import nearest_points

"""
Miscellanous functions used by multiple classes in the QC library.
"""


def catch(func, handle=lambda e: e, *args, **kwargs):
    """ Values that return an error are overwritten as np.nan...we just ignore them for now """
    try:
        return func(*args, **kwargs)
    except Exception:
        return np.nan


def haversine(lat1, lon1, lat2, lon2, to_radians=True, earth_radius=6371):
    """
    slightly modified version: of http://stackoverflow.com/a/29546836/2901002

    Calculate the great circle distance (in km) between two points
    on the earth (specified in decimal degrees or in radians)

    All (lat, lon) coordinates must have numeric dtypes and be of equal length.

    """
    if to_radians:
        lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])

    a = np.sin((lat2 - lat1) / 2.0) ** 2 + \
        np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2.0) ** 2

    return earth_radius * 2 * np.arcsin(np.sqrt(a))


def calc_speed(df, units='kts'):
    """
    Calculate speed in km/hr, mph, or kts
    """
    conversions = {'kts': 0.539957, 'mph': 0.621371}
    df['speed'] = np.nan
    if len(df.DATETIME) > 1:
        delta_time = df.DATETIME.diff().dt.total_seconds()/3600
        lat1 = df.LATITUDE.shift()
        lon1 = df.LONGITUDE.shift()
        lat2 = df.LONGITUDE
        lon2 = df.LATITUDE
        dist = haversine(lat1, lon1, lon2, lat2)
        cvf = conversions[units]
        df['speed'] = [d / t * cvf if t != 0 else np.nan for d, t in zip(dist, delta_time)]
    else:
        df['speed'] = np.nan
    return (df)


def load_yaml(filename,dict_name):
    """
    Load yaml file and return specified dictionary
    """
    with open(filename, 'r') as stream:
        try:
            for var in yaml.safe_load_all(stream):
                attrs_list = var
                return(attrs_list[dict_name])
        except yaml.YAMLError as exc:
            print('Could not open attribute file {}: {}'.format(filename, exc))

def append_to_textfile(filename,list_to_append):
    """
    Append a list, one item at a time,
    to a text file with path/name filename.
    """
    f=open(filename, "a+")
    for file in list_to_append:
        f.write(f'{file}\n')
    f.close

def list_new_files(numdays = 4, filestring = None, filedir = None, start_time = dt.datetime.now()):
    """
    Searches in filedir for all files that match filestring.
    Formats filestring and filedir with datetime strftime
    with numdays before start_date.  i.e. loops to search
    for all files between start_date and numdays before start_date
    and returns a list of all those files including path.
    """
    filelist = []
    if not filestring:
        filestring = 'MOANA*_%y%m%d*.csv'
    if not filedir:
        filedir = '/data/obs/mangopare/incoming/**/'
    for day in np.arange(numdays):
        cycle_dt = start_time - dt.timedelta(seconds=float(day*86400))
        fs = cycle_dt.strftime(filestring)
        for file in glob.glob(os.path.join(filedir,fs), recursive=True):
            filelist.append(file)
    return(filelist)

def point_on_land(point,all_shapes,tol=0):
    """
    Takes a lat/lon point and a shapefile and determines if the point lies within
    the polygons defined by the shapefile.  If it does not, then it calculates the
    minimum distance of the point from the polygon boundary.  tol is the tolerance
    in meters of distance from boundary to count as "on land"
    """

    # first check if point is on land
    is_on_land = sum([Point(point).within(shape(item)) for item in all_shapes])
    # if on land, check if within tolerance (tol) of coast
    if is_on_land and tol!=0:
        close_points = [nearest_points(shape(item),Point(point))[0].xy for item in all_shapes]
        locs = [np.array([location[1][0],location[0][0]]) for location in close_points[1:]]
        dist = np.min([haversine(lat1=point[1], lon1=point[0], lat2=loc[0], lon2=loc[1], earth_radius=6371000) for loc in locs]) 
        if dist>tol:
            return True
        else:
            return False
    else:
        return False
