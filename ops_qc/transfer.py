import os
import logging
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from glob import glob
import subprocess
import time

xr.set_options(keep_attrs=True)

# cycle_dt = dt.datetime.utcnow()


class Wrapper(object):
    """
    Wrapper class for transfer observational data onto THREDDS servers.
    Takes a list of available for publication files and transfers them from
    Acenet to dataserv for the publication into THREDDS

    Arguments:
        filelist -- list of files to transfer
        destination -- server directory for the THREDDS server
        key_file -- private key needed to transfer data into dataserv.hm

    Outputs:
        Transfers public files as netcdf into datserv
    """

    def __init__(
        self,
        filelist=None,
        key_file="/home/metocean/.ssh/id_rsa",
        destination="metocean@dataserv1.hm:/data/moana/Mangopare/public/",
        logger=logging,
        **kwargs,
    ):
        self.filelist = filelist
        self.key_file = key_file
        self.destination = destination
        self.logger = logging

    def run(self):
        filelist = self.filelist
        try:
            for files in filelist:
                jobstr = f"rsync -av -P -e 'ssh -i {self.key_file}' {files}  {self.destination}"
                proc = subprocess.run(
                    jobstr, shell=True, check=True, capture_output=True
                )
                # time.sleep(5)
        except Exception as exc:
            self.logger.error("No files to publish")
            raise type(exc)(f"No file list found due to: {exc}")
