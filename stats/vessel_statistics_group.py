import pandas as pd
import glob
import os 

files = sorted(glob.glob(os.path.join('/data/mangopare', "vesse*_01.csv")))
data=[]
for count,file in enumerate(files):
    if count ==0:
        df = pd.read_csv(file,index_col=0)
    else:
        df_2 =pd.read_csv(file,index_col=0)
        df = pd.concat([df,df_2], ignore_index=True)

df['total_duration'] = pd.to_timedelta(df['total_duration'])
df['final_time']=pd.to_datetime(df['final_time'])
df['initial_time']=pd.to_datetime(df['initial_time'])
df_grouped = df.groupby(['key']).agg({
    'vessel_id': 'first',
    'sensor_number': 'first',
    'number_of_measurements': 'sum',
    'number_of_measurements_since_public':'sum',
    'number_of_deployments':'sum',
    'number_of_deployments_since_public':'sum',
    'deployment_method': lambda x: ', '.join(x.dropna().unique()),
    'total_distance': 'sum',
    'total_distance': 'sum',
    'total_duration': 'sum',
    'geospatial_lat_max': 'max',
    'geospatial_lat_min': 'min',
    'geospatial_lon_max': 'max',
    'geospatial_lon_min': 'min',
    'initial_time': 'min',
    'final_time': 'max',
    'internal_id': lambda x: ', '.join(x.dropna().unique()),
    'publication_date': lambda x: ', '.join(x.dropna().astype(str).str.capitalize().unique()),
    'wigos_id': lambda x: ', '.join(x.dropna().unique()),
}).reset_index()
df_grouped['publication_date'] = df_grouped['publication_date'].str.replace('False, ', '')
df_grouped['active_period'] = df_grouped['final_time'] - df_grouped['initial_time']
