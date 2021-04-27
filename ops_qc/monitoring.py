import pandas as pd
import numpy as np
import xarray as xr
import logging
from utils import load_yaml

class MonitorActivity(object):
    """
    Monitoring how often fishing vessels are returning data.
    Inputs:
    """

    def __init__(self,
                 success_files = [],
                 failed_files = [],
                 logger=logging):

        self._success_files = success_files
        self._failed_files = failed_files
        self.logger = logging


    def

    def run(self):
