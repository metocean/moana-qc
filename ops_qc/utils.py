import numpy as np
import yaml
import datetime as dt
import glob

"""
Miscellanous functions used by multiple classes in the QC library.
"""


def catch(func, handle=lambda e: e, *args, **kwargs):
    """ Values that return an error are overwritten as np.nan...we just ignore them for now """
    try:
        return func(*args, **kwargs)
    except Exception as e:
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
    filelist = []
    if not filestring:
        filestring = 'MOANA*_%y%m%d*.csv'
    if not filedir:
        filedir = '/data/obs/mangopare/incoming/**/'
    for day in np.arange(numdays):    
        cycle_dt = start_time - dt.timedelta(seconds=float(day*86400))
        filestring = cycle_dt.strftime(filestring)
        for file in glob.glob(f'{filedir}{filestring}', recursive=True):
            filelist.append(file)
    return(filelist)
