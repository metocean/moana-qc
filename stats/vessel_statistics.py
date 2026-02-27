import os
import logging
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from glob import glob
import itertools
xr.set_options(keep_attrs=True)

def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers

    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    distance = R * c
    return distance

def normalize_key(key):
    return key.lower().replace('_', ' ')

def find_vessel_id(attrs):
    for key in attrs:
        normalized_key = normalize_key(key)
        if normalized_key == 'vessel id':
            vessel_id = attrs[key]
            if isinstance(vessel_id, float):
                if np.isnan(vessel_id):
                    return 'NA'
                vessel_id = str(int(vessel_id))
            elif vessel_id==0:
                vessel_id = str(int(0))
            return vessel_id
    return None

files_archive = glob('/archive/observations/mangopare/processed/*nc')
files_data = glob('/data/obs/mangopare/processed/*nc')
files = files_archive + files_data

res = 0.5
box2 = [161, 190, -52, -31]

# Calculate grid edges
x_edges2 = np.arange(box2[0] - res, box2[1] + res, res)
y_edges2 = np.arange(box2[2] - res, box2[3] + res, res)

# Get unique basenames
unique_files = {}
for file in files:
    basename = os.path.basename(file)
    if basename not in unique_files:
        unique_files[basename] = file

# Convert back to a list of unique file paths
unique_file_paths = list(unique_files.values())
unique_file_paths.remove('/archive/observations/mangopare/processed/MOANA_0175_2247_241125060947_qc.nc')
unique_file_paths.remove('/archive/observations/mangopare/processed/MOANA_0172_575_241125071849_qc.nc')


start_dates = [np.datetime64("2020-01-01"),np.datetime64("2021-01-01")]#,np.datetime64("2022-01-01")]#,np.datetime64("2023-01-01"),np.datetime64("2024-01-01")]
end_dates = [np.datetime64("2021-01-01"),np.datetime64("2022-01-01")]#,np.datetime64("2023-01-01")]#,np.datetime64("2024-01-01"),np.datetime64("2025-01-01")]
# start_dates =[np.datetime64("2023-01-01")]
# end_dates = [np.datetime64("2025-01-01")]
start_date = [np.datetime64("2020-01-01"),np.datetime64("2021-12-01")]
end_date = [np.datetime64("2020-02-01"), np.datetime64("2022-01-01")]
start_dates = pd.date_range(start_date[0], start_date[-1], freq='MS')
end_dates = pd.date_range(end_date[0], end_date[-1], freq='MS')

for start_date, end_date in zip(start_dates, end_dates):
    vessel_stats = {}
    for i, file in enumerate(unique_file_paths):
        try:
            sdn = pd.to_datetime(file[-18:-12], format="%y%m%d").to_numpy()
            year=pd.to_datetime(start_date).year
            month = pd.to_datetime(start_date).strftime('%m')  # Convert month to 2-digit string
            day = pd.to_datetime(start_date).strftime('%d')  # Convert day to 2-digit string
            if (sdn < start_date) or (sdn > end_date):
                continue
            ds = xr.open_dataset(file)
            mask = ds["QC_FLAG"] < 4
            ds = ds.where(mask, drop=True)
            if len(ds.LATITUDE) < 1:
                ds.close()
                continue

            initial_time = pd.to_datetime(np.nanmin(ds.DATETIME))
            final_time = pd.to_datetime(np.nanmax(ds.DATETIME))
            duration = final_time - initial_time

            vessel_id = find_vessel_id(ds.attrs)
            if not vessel_id:
                vessel_id = 'NA'
                print('No vessel id found')

            sensor_number = ds.attrs.get('moana_serial_number', 'NA')
            vessel_name = ds.attrs.get('vessel_name', 'NA')
            key = f"{vessel_id}-{sensor_number}"
            if key not in vessel_stats:
                vessel_stats[key] = {
                    'vessel_name': vessel_name,
                    'vessel_id': vessel_id,
                    'sensor_number': sensor_number,
                    'distance': 0,
                    'number_of_deployments': 0,
                    'duration': dt.timedelta(0),
                    'geospatial_lat_max': -np.inf,
                    'geospatial_lat_min': np.inf,
                    'geospatial_lon_max': -np.inf,
                    'geospatial_lon_min': np.inf,
                    'initial_time': initial_time,
                    'final_time': final_time,
                    'internal_id': 'NA',
                    'publication_date': 'FALSE',
                    'wigos_id': 'NA',
                    'number_of_measurements': 0,
                    'number_of_measurements_since_public':0,
                    'number_of_deployments_since_public':0,
                    'max_depths':0,
                }
            if 'start_end_dist_m' in ds.attrs:
                distance = float(ds.attrs['start_end_dist_m'])
                geospatial_lat_max = float(ds.attrs['geospatial_lat_max'])
                geospatial_lat_min = float(ds.attrs['geospatial_lat_min'])
                geospatial_lon_max = float(ds.attrs['geospatial_lon_max'])
                geospatial_lon_min = float(ds.attrs['geospatial_lon_min'])
                if geospatial_lon_max < 0:
                    geospatial_lon_max += 360
                elif geospatial_lon_min < 0:
                    geospatial_lon_min += 360
            else:
                initial_lat, initial_lon = float(ds.LATITUDE[0]), float(ds.LONGITUDE[0])
                final_lat, final_lon = float(ds.LATITUDE[-1]), float(ds.LONGITUDE[-1])
                if initial_lon < 0:
                    initial_lon += 360
                elif final_lon< 0:
                    final_lon += 360
                distance = haversine(initial_lon, initial_lat, final_lon, final_lat) * 1000
                geospatial_lat_max = max(initial_lat, final_lat)
                geospatial_lat_min = min(initial_lat, final_lat)
                geospatial_lon_max = max(initial_lon, final_lon)
                geospatial_lon_min = min(initial_lon, final_lon)
            if 'deployment_method' in ds.attrs:
                vessel_stats[key]['deployment_method'] = ds.attrs['deployment_method']
            else:
                vessel_stats[key]['deployment_method'] = 'NA'  
            if vessel_stats[key]['final_time'] < final_time:
                vessel_stats[key]['final_time'] = final_time
            if ('internal_id' in ds.attrs) and (vessel_stats[key]['internal_id'] == 'NA'):
                vessel_stats[key]['internal_id']= ds.attrs['internal_id']
            if ('publication_date' in ds.attrs) and (ds.attrs['publication_date'] != 'FALSE'):
                vessel_stats[key]['publication_date'] = ds.attrs['publication_date']
                if pd.to_datetime(ds.DATETIME.values[-1]) > pd.to_datetime(ds.attrs['publication_date'],dayfirst=True):
                    vessel_stats[key]['number_of_measurements_since_public'] += len(ds.DATETIME.values)
                    vessel_stats[key]['number_of_deployments_since_public'] += 1
                if 'wigos_id' in ds.attrs:
                    vessel_stats[key]['wigos_id'] = ds.attrs['wigos_id']
            
            vessel_stats[key]['distance'] += distance
            vessel_stats[key]['duration'] += duration
            vessel_stats[key]['number_of_deployments'] += 1
            vessel_stats[key]['number_of_measurements'] += len(ds.DATETIME.values)
            vessel_stats[key]['max_depths'] = max(vessel_stats[key]['max_depths'], np.nanmax(ds.DEPTH.values))
            vessel_stats[key]['geospatial_lat_max'] = max(vessel_stats[key]['geospatial_lat_max'], geospatial_lat_max)
            vessel_stats[key]['geospatial_lat_min'] = min(vessel_stats[key]['geospatial_lat_min'], geospatial_lat_min)
            vessel_stats[key]['geospatial_lon_max'] = max(vessel_stats[key]['geospatial_lon_max'], geospatial_lon_max)
            vessel_stats[key]['geospatial_lon_min'] = min(vessel_stats[key]['geospatial_lon_min'], geospatial_lon_min)

            ds.close()
        except Exception as e:
            logging.error(f"Failed to open {file}: {e}")
            continue
# Create a DataFrame from the vessel_stats dictionary
    data = []
    for vessel_id, stats in vessel_stats.items():
        vessel_id, sensor_number = vessel_id.split('-')
        data.append({
            'key': f"{vessel_id}-{sensor_number}",
            'vessel_id': vessel_id,
            'sensor_number': sensor_number,
            'number_of_deployments': stats['number_of_deployments'],
            'number_of_deployments_since_public': stats['number_of_deployments_since_public'],
            'number_of_measurements': stats['number_of_measurements'],
            'number_of_measurements_since_public': stats['number_of_measurements_since_public'],
            'max_depths': stats['max_depths'],
            'deployment_method': stats['deployment_method'],
            'initial_time': stats['initial_time'],
            'final_time': stats['final_time'],
            'internal_id': stats['internal_id'],
            'publication_date': stats['publication_date'],
            'wigos_id': stats['wigos_id'],
            'total_distance': stats['distance'],
            'total_duration': stats['duration'],
            'geospatial_lat_max': stats['geospatial_lat_max'],
            'geospatial_lat_min': stats['geospatial_lat_min'],
            'geospatial_lon_max': stats['geospatial_lon_max'],
            'geospatial_lon_min': stats['geospatial_lon_min']
        })
    df = pd.DataFrame(data)
    df.to_csv(f'/data/obs/mangopare/vessel_stats_{year}_{month}_{day}.csv')
    print(f"{start_date} to {end_date} saved to csv")
    del df
