import os
import logging
import json
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from glob import glob
import subprocess
import time

xr.set_options(keep_attrs=True)

cycle_dt = dt.datetime.utcnow()


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
        filelist_json=None,
        key_file="/home/metocean/.ssh/id_rsa",
        destination="metocean@dataserv1.hm:/data/moana/Mangopare/public/",
        logger=logging,
        **kwargs,
    ):
        # Extract filelist from config if passed via kwargs (from linked parent tasks)
        if filelist is None and 'config' in kwargs:
            filelist = kwargs['config'].get('filelist')
            if filelist:
                print(f"Extracted filelist from config kwargs: {len(filelist)} files")
        
        self.filelist = filelist
        self.filelist_json = filelist_json
        self.key_file = key_file
        self.destination = destination
        self.logger = logging

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt

    def _set_filelist(self):
        """
        Set the file list from either direct filelist or JSON file.
        JSON file should contain 'published_files' key with list of files.
        """
        # Read from JSON file if filelist not provided
        if not self.filelist and self.filelist_json:
            # Format the path with cycle_dt if available
            filelist_json_path = self.cycle_dt.strftime(self.filelist_json) if hasattr(self, 'cycle_dt') else self.filelist_json
            try:
                with open(filelist_json_path, 'r') as f:
                    data = json.load(f)
                # Support 'filelist', 'published_files', and 'success_files' keys
                self.filelist = data.get('published_files', data.get('published_files', data.get('success_files', [])))
                self.logger.info(f"Loaded {len(self.filelist)} files from {filelist_json_path}")
            except Exception as e:
                self.logger.error(f"Could not read filelist JSON {filelist_json_path}: {e}")
        
        if not self.filelist:
            self.logger.error(
                "No file list found, please specify. No transfer performed."
            )

    def run(self):
        self.set_cycle(cycle_dt)
        self._set_filelist()
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
