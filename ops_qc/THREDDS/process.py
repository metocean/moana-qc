import os
import logging
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from ops_qc.utils import load_yaml, import_pycallable

xr.set_options(keep_attrs=True)

cycle_dt = dt.datetime.utcnow()


class Wrapper(object):
    """
    Wrapper class for publication of observational data onto THREDDS servers.
    Takes a list of quality-controlled netcdf files and reformats the ones available
    for public access using CF-1.6 conventions and following IMOS and ARGOS conventions
    IMOS: https://s3-ap-southeast-2.amazonaws.com/content.aodn.org.au/Documents/IMOS/Conventions/IMOS_NetCDF_Conventions.pdf
    ARGOS: https://archimer.ifremer.fr/doc/00187/29825/94819.pdf

    Arguments:
        filelist -- list of files to apply transformation to
        outfile_ext -- extension to add to filenames when saving as netcdf files
        out_dir - directory to save public netcdf files (to send to THREDDS server)
        qc_class -- python class wrapper for running qc tests, returns updated xarray dataset
            that includes qc flags and updated status_file
        attr_file -- location of attribute_list.yml, default uses the one in the python
            package, should be a yaml file (see sample one in ops_qc directory)

    Returns:
        self._success_files -- list of files successfully reformatted and saved as new netcdf files

    Outputs:
        Saves public files as netcdf in out_dir
    """

    def __init__(
        self,
        filelist=None,
        outfile_ext="_qc_%y%m%d",
        out_dir=None,
        attr_file=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "attribute_list.yml"
        ),
        var_attr_dict_name="var_attr_info",
        global_attr_dict_name="global_attr_info",
        coords_attr_dict_name="coords_attr_info",
        global_attrs_dict="global_attrs",
        logger=logging,
    ):
        self.filelist = filelist
        self.outfile_ext = outfile_ext
        self.out_dir = out_dir
        self.attr_file = attr_file
        self.var_attr_dict_name = var_attr_dict_name
        self.global_attr_dict_name = global_attr_dict_name
        self.coords_attr_dict_name = coords_attr_dict_name
        self.global_attrs_dict = global_attrs_dict
        self.logger = logging
        self.coords_info = load_yaml(self.attr_file, self.coords_attr_dict_name)
        self.vars_info = load_yaml(self.attr_file, self.var_attr_dict_name)
        self.global_attr_info = load_yaml(self.attr_file, self.global_attr_dict_name)
        self.global_attrs = load_yaml(self.attr_file, self.global_attrs_dict)

    def _available_for_publication(self, filename):
        public = xr.open_dataset(filename, cache=False).attrs["public"]
        return eval(public)

    def _add_global_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.global_attrs.items():
            ## New attributes provided
            if var in self.global_attr_info:
                if "quality" in var:
                    self.ds.attrs[var] = (
                        self.global_attr_info[var][0]
                        + "="
                        + self.ds_o.attrs[self.global_attr_info[var][0]][1:-1]
                        + ", "
                        + self.global_attr_info[var][1]
                        + "="
                        + self.ds_o.attrs[self.global_attr_info[var][1]]
                    )
                else:
                    self.ds.attrs[var] = self.global_attr_info[var]
            else:
                try:
                    self.ds.attrs[var] = self.ds_o.attrs[var]
                except:
                    if "vertical_max" in var:
                        self.ds.attrs[var] = int(self.ds["DEPTH"].max())
                    elif "vertical_min" in var:
                        self.ds.attrs[var] = int(self.ds["DEPTH"].min())
                    else:
                        self.ds.attrs[var] = " "
                        self.logger.error(
                            "Could not find value for attribute: {}".format(var)
                        )
                        pass
        self.ds.attrs["publication_date"] = dt.datetime.utcnow()

    def _add_var_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.vars_info.items():
            for attr, attrinfo in varinfo.items():
                self.ds[var].attrs[attr] = attrinfo

    def _add_coords_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.coords_info.items():
            for attr, attrinfo in varinfo.items():
                if "DATE" in var and "unit" in attr:
                    self.ds[var].attrs[attr] = self.ds_o[var].attrs[attr]
                else:
                    self.ds[var].attrs[attr] = attrinfo

    def _reformat_file(self):
        self.ds_o = xr.open_dataset(self.filename, cache=False, decode_cf=False)
        ### Generate new file using the data from the previous file
        df = pd.DataFrame()
        for coords, _ in coords_info.items():
            df[coords] = self.ds_o[coords]
        for var, _ in vars_info.items():
            df[var] = self.ds_o[var]
        df = df.set_index(["DATETIME"])
        self.ds = xr.Dataset.from_dataframe(df)
        for coords, _ in coords_info.items():
            self.ds = self.ds.assign_coords({coords: self.ds[coords]})
        ## Adding attributes
        self._add_global_attrs()
        self._add_vars_attrs()
        self._add_coords_attrs()

    def run(self):
        for file in self.filelist:
            if self._available_for_publication(file):
                self.filename = file
                self._reformat_file()
                head, tail = os.path.split(self.filename)
                if not self.out_dir:
                    self.out_dir = head
                # create (mkdir) out_dir if it doesn't exist
                self._initialize_outdir(self.out_dir)
                savefile = "{}{}{}{}".format(
                    self.out_dir, os.path.splitext(tail)[0], self.outfile_ext, ".nc"
                )
                self.ds.to_netcdf(savefile, mode="w", format="NETCDF4")
                # self._saved_files.append(savefile)
