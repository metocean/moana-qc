import os
import logging
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from glob import glob
from ops_qc.utils import load_yaml

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
        outfile_ext="published",
        out_dir=None,
        attr_file=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "attribute_list.yml"
        ),
        var_attr_dict_name="vars_attr_info",
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

    # def set_cycle(self, cycle_dt):
    #     self.cycle_dt = cycle_dt

    def _available_for_publication(self, filename):
        try:
            # Check if data is public
            public = xr.open_dataset(filename, cache=False, engine="netcdf4").attrs[
                "public"
            ]
            # Check if the current data is after the agreement signature date
            self.first_measurement = xr.open_dataset(
                filename, cache=False, engine="netcdf4"
            )["DATETIME"][0].values
            self.last_measurement = xr.open_dataset(
                filename, cache=False, engine="netcdf4"
            )["DATETIME"][-1].values
            publication_date = dt.datetime.strptime(
                xr.open_dataset(filename, cache=False, engine="netcdf4").attrs[
                    "publication_date"
                ],
                "%d/%m/%Y",
            )
            publication_date = np.datetime64(publication_date)
            if self.first_measurement - publication_date > 0:
                return eval(public)
            else:
                return False
        except:
            return False

    def _add_global_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.global_attrs.items():
            ## New attributes provided
            if var in self.global_attr_info:
                if "quality_control_log" in var:
                    self.ds.attrs[var] = (
                        self.global_attr_info[var][0]
                        + "="
                        + self.ds_o.attrs[self.global_attr_info[var][0]][1:-1]
                        + ", "
                        + self.global_attr_info[var][1]
                        + "="
                        + self.ds_o.attrs[self.global_attr_info[var][1]]
                    )
                elif "instrument" in var:
                    max_depth = self.ds_o.attrs["max_lifetime_depth"].split()[0]
                    if max_depth > 200:
                        self.ds.attrs[var] = self.global_attr_info[var].format(1000)
                    else:
                        self.ds.attrs[var] = self.global_attr_info[var].format(200)
                else:
                    self.ds.attrs[var] = self.global_attr_info[var]
            else:
                try:
                    self.ds.attrs[var] = self.ds_o.attrs[varinfo]
                except:
                    if "vertical_max" in var:
                        self.ds.attrs[var] = str(
                            np.round(self.ds["DEPTH"].max().values, 1)
                        )
                    elif "vertical_min" in var:
                        self.ds.attrs[var] = str(
                            np.round(self.ds["DEPTH"].min().values, 1)
                        )
                    elif "time_coverage_start" in var:
                        self.ds.attrs[var] = pd.to_datetime(
                            self.first_measurement
                        ).strftime("%d/%m/%Y %H:%M:%S")
                    elif "time_coverage_end" in var:
                        self.ds.attrs[var] = pd.to_datetime(
                            self.last_measurement
                        ).strftime("%d/%m/%Y %H:%M:%S")
                    else:
                        self.ds.attrs[var] = ""
                        self.logger.error(
                            "Could not find value for attribute: {}".format(var)
                        )
                        pass
        self.ds.attrs["publication_date"] = dt.datetime.utcnow().strftime(
            "%d/%m/%Y %H:%M"
        )

    def _add_var_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.vars_info.items():
            if "new_name" in varinfo:
                var = varinfo["new_name"]
            for attr, attrinfo in varinfo.items():
                if "new_name" not in attr:
                    self.ds[var].attrs[attr] = attrinfo

    def _add_coords_attrs(self):
        """
        Loads global variable attributes from attribute file.
        """
        for var, varinfo in self.coords_info.items():
            if "new_name" in varinfo:
                var = varinfo["new_name"]
            for attr, attrinfo in varinfo.items():
                if "new_name" not in attr:
                    self.ds[var].attrs[attr] = attrinfo

    def _reformat_file(self):
        self.ds_o = xr.open_dataset(self.filename, cache=False, decode_cf=False)
        ### Generate new file using the data from the previous file
        df = pd.DataFrame()
        for coords, items in self.coords_info.items():
            if "new_name" in items:
                coordsn = items["new_name"]
                df[coordsn] = self.ds_o[coords]
            else:
                df[coords] = self.ds_o[coords]

        for var, items in self.vars_info.items():
            if "new_name" in items:
                varn = items["new_name"]
                df[varn] = self.ds_o[var]
            else:
                df[var] = self.ds_o[var]
        df = df.set_index(["DATE_TIME"])
        self.ds = xr.Dataset.from_dataframe(df)
        for coords, _ in self.coords_info.items():
            if "new_name" in items:
                coords = items["new_name"]
            self.ds = self.ds.assign_coords({coords: self.ds[coords]})
        ## Adding attributes
        self._add_coords_attrs()
        self._add_var_attrs()
        self._add_global_attrs()

    def _initialize_outdir(self, dir_path):
        """
        Check if outdir exists, create if not
        """
        try:
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
        except Exception as exc:
            self.logger.error(
                "Could not create specified directory to save publishable files in: {}".format(
                    exc
                )
            )

    def run(self):
        self.filelist = cycle_dt.strftime(self.filelist)
        self.filelist = glob(self.filelist)
        for file in self.filelist:
            if self._available_for_publication(file):
                self.filename = file
                self._reformat_file()
                head, tail = os.path.split(self.filename)
                if not self.out_dir:
                    self.out_dir = head
                # create (mkdir) out_dir if it doesn't exist
                self._initialize_outdir(self.out_dir)
                name = os.path.splitext(tail)[0].split("_")
                end_date_name = pd.to_datetime(self.last_measurement).strftime(
                    "%Y%m%d_%H%M%S"
                )
                savefile = "{}{}{}{}".format(
                    self.out_dir,
                    "_".join([name[0], end_date_name]),
                    self.outfile_ext,
                    ".nc",
                )
                self.ds.to_netcdf(savefile, mode="w", format="NETCDF4")
                # self._saved_files.append(savefile)
