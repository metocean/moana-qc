'''
Miscellanous functions used by multiple classes in the QC library.
'''

def catch(func, handle=lambda e : e, *args, **kwargs):
    ''' Values that return an error are overwritten as np.nan...we just ignore them for now '''
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

    a = np.sin((lat2-lat1)/2.0)**2 + \
        np.cos(lat1) * np.cos(lat2) * np.sin((lon2-lon1)/2.0)**2

    return earth_radius * 2 * np.arcsin(np.sqrt(a))

def calc_speed(df,units = 'kts'):
    '''
    Calculate speed in km/hr, mph, or kts
    '''
    conversions = {'kts':0.539957,'mph':0.621371}
    self.df['speed'] = np.nan
    if (len(df) != 0):
        delta_time = df.DATETIME.to_series().diff().dt.hours
        lat1 = df.LATITUDE.shift()
        lon1 = df.LONGITUDE.shift()
        lat2 = df.loc[1:, 'LONGITUDE']
        lon2 = df.loc[1:, 'LATITUDE']
        dist = haversine(lat1, lon1, lon2, lat2)
        factor = conversions[units]
        df['speed'] = [d / t * factor if t != 0 else np.nan for d,t in zip(dist,delta_time)]
    else:
        df['speed'] = np.nan
    return(df)
