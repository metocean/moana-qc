import pandas as pd
import numpy as np
import xarray as xr
import requests
import logging


class CheckFishserve(object):
    """
    Read FishServe database and compare to fisher metadata.
    Inputs:
        vessel_num = vessel registration number (painted on hull)
    """

    def __init__(self,
                 vessel_num,
                 logger=logging,
                 apiEndpoint='https://licence.uat.kupe.fishserve.co.nz/api/vessels/get/',
                 **kwargs):

        self.vesel_num = vessel_num
        self.apiEndpoint = apiEndpoint
        self.logger = logging

    def request_data(vessel_num,apiEndpoint):
        url = apiEndpoint+str(vessel_num)
        r = requests.get(url)
        return r.json()

    def run(self):
        vessel_info = self.request_data(self.vessel_num,self.apiEndpoint)

        pass
