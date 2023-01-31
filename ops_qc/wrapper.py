import os
import logging
import pytz
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from ops_core.utils import import_pycallable
from ops_qc.utils import catch, haversine, start_end_dist

cycle_dt = dt.datetime.now()

class QcWrapper(object):
    """Wrapper class for observational data quality control.  Incorporates transferring files from
    an incoming directory to a new directory.

    """

    def __init__(
        self,
        filelist=None,
        outfile_ext="_qc_%y%m%d",
        out_dir=None,
        test_list_1=None,
        test_list_2=None,
        fishing_metafile="/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv",
        metafile_username=[],
        metafile_token=[],
        status_file_ext="_%y%m%d",
        status_file_dir="",
        datareader={},
        metareader={},
        preprocessor={},
        qc_class={},
        save_flags=False,
        convert_p_to_z=True,
        default_latitude=-40,
        attr_file=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "attribute_list.yml"
        ),
        startstring="DateTime (UTC)",
        splitstring="due to:",
        dateformat="%Y%m%dT%H%M%S",
        gear_class={
            "Bottom trawl": "mobile",
            "Potting": "stationary",
            "Long lining": "stationary",
            "Trawling": "mobile",
            "Midwater trawl": "mobile",
            "Purse seine netting": "stationary",
            "Bottom trawling": "mobile",
            "Research": "mobile",
            "Education": "mobile",
            "Bottom trawler": "mobile",
            "Bottom long line": "mobile",
            "Waka": "mobile",
            "Danish seining": "stationary",
            "Netting": "stationary",
            "Set netting": "stationary",
            "Dredge": "mobile",
            "Instrument deployment": "mobile",
            "Potting, long lining": "stationary",
            "Diving": "stationary",
            "Trolling": "mobile"
        },
        metadata_columns={
            "gear_class": "Gear Class",
            "vessel_email": "Contact email",
            "vessel_name": "Vessel name",
            "email_status": "Email Status",
            "email_frequency": "Email Frequency",
            "expected_deck_unit_serial_number": "Deck unit serial number",
        },
        logger=logging,
        **kwargs,
    ):

        self.filelist = filelist
        self.outfile_ext = outfile_ext
        self.out_dir = out_dir
        self.test_list_1 = test_list_1
        self.test_list_2 = test_list_2
        self.metafile = fishing_metafile
        self.metafile_username = metafile_username
        self.metafile_token = metafile_token
        self.status_file_ext = status_file_ext
        self.status_file_dir = status_file_dir
        self.datareader_class = datareader
        self.metareader_class = metareader
        self.preprocessor_class = preprocessor
        self.qc_class = qc_class
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.default_latitude = default_latitude
        self.attr_file = attr_file
        self.startstring = startstring
        self.splitstring = splitstring
        self.dateformat = dateformat
        self.gear_class = gear_class
        self.metadata_columns = metadata_columns
        self._default_datareader_class = "ops_qc.readers.MangopareStandardReader"
        self._default_metareader_class = "ops_qc.readers.MangopareMetadataReader"
        self._default_preprocessor_class = "ops_qc.preprocess.PreProcessMangopare"
        self._default_qc_class = "ops_qc.apply_qc.QcApply"
        self.logger = logging
        self.status_dict_keys = [
            "filename",
            "baseline",
            "cellular_signal_strength",
            "date_quality_controlled",
            "deck_unit_battery_percent",
            "deck_unit_battery_voltage",
            "download_time",
            "gear_class",
            "max_lifetime_depth",
            "moana_battery",
            "moana_serial_number",
            "moana_calibration_date",
            "qc=1",
            "qc=2",
            "qc=3",
            "qc=4",
            "reset_codes",
            "reset_codes_data",
            "saved",
            "failed",
            "failure_mode",
            "total_obs",
            "detailed_error"
        ]

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt
        if self.out_dir:
            self.out_dir = cycle_dt.strftime(self.out_dir)
        if self.outfile_ext:
            self.outfile_ext = cycle_dt.strftime(self.outfile_ext)

    #     self._proxy.set_cycle(cycle_dt)

    def _set_class(self, in_class, default_class):
        klass = in_class.pop("class", default_class)
        out_class = import_pycallable(klass)
        self.logger.info("Using class: %s " % klass)
        return out_class

    def _set_all_classes(self):
        try:
            self.datareader = self._set_class(
                self.datareader_class, self._default_datareader_class
            )
            self.metareader = self._set_class(
                self.metareader_class, self._default_metareader_class
            )
            self.preprocessor = self._set_class(
                self.preprocessor_class, self._default_preprocessor_class
            )
            self.qc_class = self._set_class(
                self.qc_class, self._default_qc_class
            )
        except Exception as exc:
            self.logger.error(
                "Unable to set required classes for qc: {}".format(exc))
            raise type(exc)(f'Unable to set requred classes for qc due to: {exc}')


    def _set_filelist(self):
        try:
            if hasattr(self, "_success_files"):
                self.files_to_qc = self._success_files
            else:
                self.files_to_qc = self.filelist
        except Exception as exc:
            self.logger.error(
                "No file list found, please specify.  No QC performed.")
            raise type(exc)(f'No file list found, no QC performed due to: {exc}')


    def _save_qc_data(self, filename):
        """
        Save qc'd data as netcdf files.  If no outdir specified,
        saves in same directory as original file.
        """
        try:
            head, tail = os.path.split(filename)
            if not self.out_dir:
                self.out_dir = head
            # create (mkdir) out_dir if it doesn't exist
            self._initialize_outdir(self.out_dir)
            savefile = "{}{}{}{}".format(
                self.out_dir, os.path.splitext(
                    tail)[0], self.outfile_ext, ".nc"
            )
            self.ds.to_netcdf(savefile, mode="w", format="NETCDF4")
            # self._saved_files.append(savefile)
            self.status_dict.update({"saved": "yes"})
            self._saved_files.append(savefile)
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Save QC File Failed"}
            )
            self.logger.error(
                "Could not save qc data from {}: {}".format(filename, exc)
            )
            # self._failed_files.append(f'{filename}: Save QC File Failed')

    def _save_status_data(self):
        """
        Save self._success_files and self._failed_files as text files.
        If status_file_dir is not specified, saves in same directory as
        qc'd data.
        """
        try:
            if not self.status_file_dir:
                self.status_file_dir = self.out_dir
            # create (mkdir) status_file_dir if it doesn't exist
            self._initialize_outdir(self.status_file_dir)
            # create all the status files in self.save_file_dict
            #           for name,data in save_file_dict:
            basefile = f"status_file{self.status_file_ext}.csv"
            filename = cycle_dt.strftime(
                os.path.join(self.status_file_dir, basefile))
            self._status_data.to_csv(
                filename, mode="a", header=not os.path.isfile(filename), index=False
            )
        except Exception as exc:
            self.logger.error("Could not save status files: {}".format(exc))

    def _initialize_outdir(self, dir_path):
        """
        Check if outdir exists, create if not
        """
        try:
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
        except Exception as exc:
            self.logger.error(
                "Could not create specified directory to save qc files in: {}".format(
                    exc
                )
            )
            raise type(exc)(f'Could not create specified directory to save qc files in due to: {exc}')


    def convert_pressure_to_depth(self):
        """
        Converts pressure to depth in the ocean either using the
        mean latitude of the observations or using a default_latitude
        """
        try:
            if not np.isnan(np.nanmean(self.ds["LATITUDE"])):
                d_lat = np.nanmean(self.ds["LATITUDE"])
            else:
                d_lat = self.default_latitude
            depth = [
                sw.eos80.dpth(catch(lambda: float(z)), d_lat)
                for z in self.ds["PRESSURE"]
            ]
            self.ds["DEPTH"] = xr.Variable(
                dims="DATETIME",
                data=depth,
                attrs={"units": "[m]", "standard_name": "depth"},
            )
            self.ds = self.ds.drop("PRESSURE")
            self.ds = self.ds.rename({"PRESSURE_QC": "DEPTH_QC"})
            return self.ds
        except Exception as exc:
            self.logger.error(
                "Could not convert pressure to depth, leaving as pressure: {}".format(
                    exc
                )
            )
            pass

    def _calc_positions(self, filename, surface_pressure=10, qcrange=[1,2]):
        """
        Calculate locations for either stationary or mobile gear.
        Current state of this code assumes all stationary locations
        in one CSV file are the SAME.  NOT NECESSARILY TRUE!  Hence
        the commented out regions...eventually will use those.
        """
        try:
            if self.ds.attrs['gear_class'] == 'stationary':
                # this needs work
                if 'LOCATION_QC' in self.ds.data_vars:
                    ds2 = self.ds.where(self.ds['LOCATION_QC'].isin(qcrange), drop=True)
                else:
                    ds2 = self.ds
                if 'DATETIME_QC' in ds2.data_vars:
                    ds2 = ds2.where(
                        ds2['DATETIME_QC'].isin(qcrange), drop=True)
                lat = np.nanmean(
                    [ds2.LATITUDE.values[0], ds2.LATITUDE.values[-1]])
                lon = np.nanmean(
                    [ds2.LONGITUDE.values[0], ds2.LONGITUDE.values[-1]])
                lons = np.ones_like(self.ds['LONGITUDE'])*lon
                lats = np.ones_like(self.ds['LATITUDE'])*lat
                self.ds['LATITUDE'] = xr.DataArray(lats, dims=['DATETIME'])
            if self.ds.attrs['gear_class'] == 'mobile':
                lons = self.ds['LONGITUDE']
            # convert to 0-360 for both stationary and mobile gear:
            lons = [l % 360 for l in lons]
            self.ds['LONGITUDE'] = xr.DataArray(lons, dims=['DATETIME'])
        except Exception as exc:
            self.logger.error(
                f"Position could not be calculated for {filename}: {exc}")
            raise type(exc)(f'Could not calculate stationary positions (len={len(self.ds.TEMPERATURE)}) due to: {exc}')

    def _calc_location_attrs(self,filename):
        """
        Assigns derived position attributes to netdf and
        calculates the start_end_dist
        """
        try:
            self.ds.attrs['geospatial_lat_max'] = "%.6f" % np.nanmax(
                self.ds.LATITUDE.values)
            self.ds.attrs['geospatial_lat_min'] = "%.6f" % np.nanmin(
                self.ds.LATITUDE.values)
            self.ds.attrs['geospatial_lon_max'] = "%.6f" % np.nanmax(
                self.ds.LONGITUDE.values)
            self.ds.attrs['geospatial_lon_min'] = "%.6f" % np.nanmin(
                self.ds.LONGITUDE.values)
            sed = start_end_dist(self.ds)
            self.ds.attrs['start_end_dist_m'] = "%.2f" % sed
        except Exception as exc:
            self.logger.error(
                f"Position attrs not assigned for {filename}: {exc}")
            raise type(exc)(f'Position attrs or start_end_dist not assigned due to: {exc}')


    def _postprocess(self, filename):
        """
        If gear class is not unknown, apply QC, convert pressure to depth
        if desired, check if any bad data, save file.
        """
        try:
            # only save files with at least some good data
            if np.nanmin(self.ds["QC_FLAG"]) < 4:
                if self.convert_p_to_z:
                    self.ds = self.convert_pressure_to_depth()
                self._save_qc_data(filename)
                self.status_dict["total_obs"] = len(self.ds["DATETIME"])
                # this is annoying but it didn't want to unpack single tuples...
                values, counts = np.unique(
                    self.ds["QC_FLAG"].values, return_counts=True
                )
                if len(values) > 1:
                    for values, counts in zip(values, counts):
                        self.status_dict[f"qc={values}"] = counts
                else:
                    self.status_dict[f"qc={values[0]}"] = counts[0]
            else:
                self.status_dict.update(
                    {"failed": "yes",
                        "failure_mode": "No Good Data (all QC Flags = 4)"}
                )
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Post-Processing Failed"})
            self.logger.error(
                f"Could not postprocess {filename} due to {exc}")

    def _qc_files(self, test_list, filename):
        try:
            self.ds = self.qc_class(
                self.ds,
                test_list,
                self.save_flags,
                self.attr_file,
                ).run()
        except Exception as exc:
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Apply QC Tests Failed"})
            self.logger.error(
                f"Could not qc {filename} due to {exc}")

    def _update_status(self, filename):
        try:
            status_dict2 = {
                k: self.status_dict[k]
                for k in self.status_dict_keys
                if k in self.status_dict
            }
            status_dict2['filename'] = filename
            self._status_data = self._status_data.append(
                status_dict2, ignore_index=True)
        except Exception:
            self.logger.error(f"Could not append status info for {filename}")

    def _status_checks(self, filename):
        check_passed = True
        if not hasattr(self.ds, "expected_deck_unit_serial_number"):
            if "failed" not in self.status_dict:
                self.status_dict.update(
                    {
                        "failed": "yes",
                        "failure_mode": "Expected deck unit unknown.",
                    }
                )
            self._update_status(filename)
            check_passed = False
        elif int(self.ds.attrs["deck_unit_serial_number"]) != int(
            self.ds.attrs["expected_deck_unit_serial_number"]
        ):
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Deck units do not match!"}
            )
            self._update_status(filename)
            check_passed = False
        elif self.ds.attrs["gear_class"] == "unknown":
            self.status_dict.update(
                {"failed": "yes", "failure_mode": "Gear Class Unknown"}
            )
            self._update_status(filename)
            check_passed = False
        return check_passed

    def _process_files(self):
        """Read, reprocess, and apply qc"""
        self._status_data = pd.DataFrame(columns=self.status_dict_keys)
        self._saved_files = []
        self._set_filelist()

        # apply qc
        for filename in self.files_to_qc:
            self.status_dict = {}
            try:
                self.ds = self.datareader(filename=filename).run()
                self.ds, self.status_dict = self.preprocessor(
                    ds=self.ds,
                    fisher_metadata=self.fisher_metadata,
                    attr_file=self.attr_file,
                    metadata_columns=self.metadata_columns,
                    status_dict=self.status_dict
                ).run()
                passed = self._status_checks(filename)
                if not passed:
                    continue
                self._qc_files(self.test_list_1,filename)
                self._calc_location_attrs(filename)
                self._calc_positions(filename)
                if self.ds.attrs['gear_class'] == 'stationary':
                    self._qc_files(self.test_list_2,filename)
                self._postprocess(filename)
                self._update_status(filename)
            except Exception as exc:
                #import ipdb; ipdb.set_trace()
                if self.splitstring in str(exc):
                    estr = str(exc).split(self.splitstring)
                    self.status_dict.update({"failed": "yes","failure_mode":estr[0],"detailed_error":estr[1]})
                else:
                    self.status_dict.update({"failed": "yes","failure_mode":str(exc),"detailed_error":"NA"})
                self._update_status(filename)
                self.logger.error(
                    "Could not qc data from {}. Traceback: {}".format(
                        filename, exc)
                )
        self._save_status_data()
        self._success_files = self._saved_files

    def run(self):
        # set all readers/preprocessors
        self.set_cycle(cycle_dt)
        self._set_all_classes()
        # load metadata common for all files
        self.fisher_metadata = self.metareader(
            metafile=self.metafile,
            gear_class=self.gear_class,
            username=self.metafile_username,
            token=self.metafile_token,
        ).run()

        if len(self.filelist) < 1 or not self.filelist:
            self.logger.info(
                'No files in filelist, exiting without performing qc and returning "None".'
            )
            self._success_files = None
        else:
            self._process_files()
        return self._success_files
