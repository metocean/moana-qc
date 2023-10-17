import os
import logging
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from ops_qc.utils import catch, start_end_dist, import_pycallable

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
        datareader -- python class to read csv file, returns an xarray dataset
        preprocessor -- python class to preprocess data from datareader, returns updated
            xarray dataset and updated status_file
        qc_class -- python class wrapper for running qc tests, returns updated xarray dataset
            that includes qc flags and updated status_file
        attr_file -- location of attribute_list.yml, default uses the one in the python
            package, should be a yaml file (see sample one in ops_qc directory)

    Returns:
        self._success_files -- list of files successfully reformatted and saved as new netcdf files

    Outputs:
        Saves public files as netcdf in out_dir
    """        
        metadata_columns={
            "deck_unit_firmware_version" : "DU Firmware",
            "deck_unit_battery_voltage" : "DU Battery Voltage",
            "deck_unit_battery_percent" : "DU Battery Percentage",
            "upload_position" : "Upload Position",
            "upload_signal_strength" : "Upload Signal Strength",
            "upload_attempts" : "Upload Attempts",
            "upload_time" : "Upload Time" ,
            "download_position" : "Download Position" ,
            "download_time" : "Download Time" ,
            "moana_serial_number" : "MOANA Serial Number" ,
            "moana_firmware" : "MOANA Firmware" ,
            "protocol_version" : "Protocol Version" ,
            "moana_calibration_date" : "Sensor Calibration Date",
            "reset_codes" : "Reset Codes",
            "moana_battery" : "Sensor Battery",
            "max_lifetime_depth" : "Max Lifetime Depth",
            "baseline" : "Baseline",
            "date_quality_controlled" : "QC Data" ,
            "quality_control_repository" : "QC Repository",
            "qc_package_version" : "QC Version",
            "moana_serial_number": "Serial Number",
            "programme_name": "Programme",
            "public": "Public",
            "publication_date": "Publication Date",
            "contact": "Contact",
            "author": "Author",
            "references": "References" ,
            "history" : "History" ,
            "acknowledgement": "Acknowledgement",
            "qc_tests_applied": "QC Applied Tests",
            "qc_tests_failed": "QC Failed Tests",
            "geospatial_lat_max": "Maximum Latitude",
            "geospatial_lat_min": "Minimum Latitude",
            "geospatial_lon_max": "Maximum Longitude",
            "geospatial_lon_min": "Minimum Longitude",
            "start_end_dist_m" : "Distance Travelled"
        },


        global_attributes = {
            "title",
            "institution",
            "source",
            "history",
            "references",
            "comment",
            "user_manual_version",
            "Conventions"
        }

        dimensions = {
            "DATE_TIME",
            "N_PARAM",
            "N_SENSOR",
        }

        general_info = {
            "DATA_TYPE":{"long_name": "Data type", "conventions": "Argo reference table", "_FillValue": ""},
            "FORMAT_VERSION":{"long_name": "File Format version", "_FillValue": ""},
            "HANDBOOK_VERSION"{"long_name": "Data handbook version", "_FillValue": ""}, 
            "DATE_CREATION": {"long_name" : "Date of file creation", "conventions":"YYYYMMDDHHMISS", "_FillValue": ""},
            "DATA_UPDATE" : {"long_name" : "Date of update of this file", "conventions":"YYYYMMDDHHMISS", "_FillValue": ""},
        }

        float_char = {
            "PLATFORM_NUMBER",
            "PLATFORM_WIGOS_ID",
            "PTT",
            "TRANS_SYSTEM",
            "TRANS_SYSTEM_ID",
            "TRANS_FREQUENCY",
            "POSITIONING_SYSTEM",
            "PLATFORM_FAMILY",
            "PLATFORM_TYPE",
            "PLATFORM_MAKER",
            "FIRMWARE_VERSION",
            "MANUAL_VERSION",
            "FLOAT_SERIAL_NO",
            "STANDARD_FORMAT_ID",
            "DAC_FORMAT_ID",
            "WMO_INST_TYPE",
            "PROJECT_NAME",
            "DATA_CENTRE",
            "PI_NAME",
            "ANOMALY",
            "BATTERY TYPE",
            "BATTERY PACKS",
            "FLOAT_OWNER",
            "OPERATING_INSTITUTION",
            "CUSTOMISATION",
        }

        mission_info = {
            "LAUNCH_DATE",
            "LAUNCH_LATITUDE",
            "LAUNCH_LONGITUDE",
            "LAUNCH_QC",
            "START_DATE",
            "START_DATE_QC",
            "STARTUP_DATE",
            "STARTUP_DATE_QC",
            "DEPLOYMENT_PLATFORM",
            "DEPLOYMENT_CRUISE_ID",
            "END_MISSION_DATE",
            "END_MISSION_STATUS",
        }

        parameter_info = {
            "PARAMETER",
            "PARAMETER_SENSOR",
            "PARAMETER_UNITS",
            "PARAMETER_ACCURACY",
            "PARAMETER_RESOLUTION"
        }

        IMOS = {
            "instrument_sample_interval",
            "quality_control_log",
            "geospatial_vertical_max",
            "geospatial_vertical_min",
            "standard_name_vocabulary"
            "toolbox_version",

        }