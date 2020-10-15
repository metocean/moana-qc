import numpy as np
import pandas as pd
from datetime import datetime
import logging

class MangopareStandardReader:
    '''
    Read Mangopare temperature and pressure data for applying quality control.
    Right now this is all done using pandas dataframes for consistency with
    the Berring Data Collective.
    '''
    def __init__(self, filename,
                 skiprows = 11,
                 dateformat = '%Y%m%dT%H%M%S',
                 logger = logging,
                 index_file = '/source/Data/Tiro_Moana/Tiral_fisherman_database.csv'
                  **kwargs):
        self.filename = filename
        self.skiprows = skiprows
        self.dateformat = dateformat
        self.logger = logger
        self.index_file = index_file

    def load_moana_standard(self):
        self.ds = pd.read_csv(self.filename,skiprows = self.skiprows,error_bad_lines=False)
        self.ds.rename(columns={'Depth m': 'PRESSURE', 'DateTime (UTC)':'DATETIME', 'Lat':'LATITUDE','Lon':'LONGTIUDE','Temperature C':'TEMPERATURE'}, inplace=True)
        self.ds.DATETIME = pd.to_datetime(self.ds['DATETIME'], format=dateformat, errors='coerce')
        self.ds = self.ds.dropna().to_xarray()  
        f = open(filename)
        for i in range(skiprows):
            row = f.readline().split(',')
            self.ds.attrs[row[0]] = row[1]
    
    def load_fisher_metadata(self):
        

    def run():
        self.ds = load_moana_standard()
        self._read_raw_data()
        if self.filter_empty_rows:
            self._filter_empty_rows()
        return(self.data)

