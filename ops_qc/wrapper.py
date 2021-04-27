import os
import logging
import pytz
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import netCDF4
import datetime as dt
from ops_core.utils import import_pycallable
from utils import catch, append_to_textfile

cycle_dt = dt.datetime.now()

class QcWrapper(object):
    '''Wrapper class for observational data quality control.  Incorporates transferring files from
    an incoming directory to a new directory.

    '''
    def __init__(self,
                filelist = None,
                outfile_ext = '_qc',
                out_dir = None,
                test_list = None,
                fishing_metafile = '/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv',
                status_file_ext = '_%y%m%d',
                status_file_dir = '',
                datareader = {},
                metareader = {},
                preprocessor = {},
                qc_class = {},
                save_flags = False,
                convert_p_to_z = True,
                default_latitude = -40,
                attr_file = 'attribute_list.yml',
                startstring = "DateTime (UTC)",
                dateformat = '%Y%m%dT%H%M%S',
                gear_class = {'Bottom trawl':'mobile','Potting':'stationary','Long lining':'mobile','Trawling':'mobile', 'Midwater trawl': 'mobile','Purse seine netting':'mobile'},
                logger = logging):

        self.filelist = filelist
        self.outfile_ext = outfile_ext
        self.out_dir = out_dir
        self.test_list = test_list
        self.metafile = fishing_metafile
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
        self.dateformat = dateformat
        self.gear_class = gear_class
        self._default_datareader_class = 'readers.MangopareStandardReader'
        self._default_metareader_class = 'readers.MangopareMetadataReader'
        self._default_preprocessor_class = 'preprocess.PreProcessMangopare'
        self._default_qc_class = 'apply_qc.QcApply'
#        self.save_file_dict = {'status_file':self._status_data}
        self.logger = logging
        self.status_dict_keys = ['Baseline',
                                 'Celular signal strength',
                                 'Date quality controlled',
                                 'Deck unit battery percent',
                                 'Deck unit battery voltage',
                                 'Download Time',
                                 'Gear Class',
                                 'Max Lifetime Depth',
                                 'Moana Battery',
                                 'Moana Serial Number',
                                 'Moana calibration date',
                                 'QC=1',
                                 'QC=2',
                                 'QC=3',
                                 'QC=4',
                                 'Reset Codes',
                                 'Reset Codes Data',
                                 'Saved',
                                 'Failed',
                                 'Failure Mode',
                                 'Total Obs']

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt
        self.out_dir = cycle_dt.strftime(self.out_dir)
    #     self._proxy.set_cycle(cycle_dt)

    def _set_class(self,in_class,default_class):
        klass = in_class.pop('class', default_class)
        out_class = import_pycallable(klass)
        self.logger.info('Using class: %s ' % klass)
        return(out_class)

    def _set_all_classes(self):
        try:
            self.datareader = self._set_class(self.datareader_class,self._default_datareader_class)
            self.metareader = self._set_class(self.metareader_class,self._default_metareader_class)
            self.preprocessor = self._set_class(self.preprocessor_class,self._default_preprocessor_class)
            self.qc_class = self._set_class(self.qc_class,self._default_qc_class)
        except Exception as exc:
            self.logger.error('Unable to set required classes for qc: {}'.format(exc))
            raise exc

    def _set_filelist(self):
        try:
            if hasattr(self, '_success_files'):
                self.files_to_qc = self._success_files
            else:
                self.files_to_qc = self.filelist
        except Exception as exc:
            self.logger.error('No file list found, please specify.  No QC performed.')
            raise exc

    def _save_qc_data(self,filename):
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
            savefile = '{}{}{}{}'.format(self.out_dir,os.path.splitext(tail)[0],self.outfile_ext,'.nc')
            self.ds.to_netcdf(savefile,mode="w",format="NETCDF4")
            #self._saved_files.append(savefile)
            self.status_dict.update({'Saved':'yes'})
        except Exception as exc:
            self.logger.error('Could not save qc data from {}: {}'.format(filename, exc))
            #self._failed_files.append(f'{filename}: Save QC File Failed')
            self.status_dict.update({'Failed':'yes','Failure Mode':'Save QC File Failed'})


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
            basefile = f'status_file{self.status_file_ext}.csv'
            filename = cycle_dt.strftime(os.path.join(self.status_file_dir,basefile))
#                append_to_textfile(filename,filelist)
            pd.DataFrame.from_dict(self._status_data).transpose().to_csv(filename)
        except Exception as exc:
            self.logger.error('Could not save status files: {}'.format(exc))

    def _initialize_outdir(self,dir_path):
        """
        Check if outdir exists, create if not
        """
        try:
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
        except Exception as exc:
            self.logger.error('Could not create specified directory to save qc files in: {}'.format(exc))
            raise exc

    def convert_pressure_to_depth(self):
        '''
        Converts pressure to depth in the ocean either using the
        mean latitude of the observations or using a default_latitude
        '''
        try:
            if not np.isnan(np.nanmean(self.ds['LATITUDE'])):
                d_lat = np.nanmean(self.ds['LATITUDE'])
            else:
                d_lat = self.default_latitude
            depth = [sw.eos80.dpth(catch(lambda: float(z)),d_lat) for z in self.ds['PRESSURE']]
            self.ds['DEPTH'] = xr.Variable(dims = 'DATETIME', data = depth, attrs={'units':'[m]','standard_name':'depth'})
            self.ds = self.ds.drop('PRESSURE')
            return(self.ds)
        except Exception as exc:
            self.logger.error('Could not convert pressure to depth, leaving as pressure: {}'.format(exc))
            pass

    def _processed_classified_gear(self,filename):
        """
        If gear class is not unknown, apply QC, convert pressure to depth
        if desired, check if any bad data, save file.
        """
        self.ds = self.qc_class(self.ds,self.test_list,self.save_flags,self.convert_p_to_z,self.default_latitude,self.attr_file).run()
        # only save files with at least some good data
        #import ipdb; ipdb.set_trace()
        if np.nanmin(self.ds['QC_FLAG'])<4:
            if self.convert_p_to_z:
                self.ds = self.convert_pressure_to_depth()
            self._save_qc_data(filename)
#            if np.nanmax(self.ds['QC_FLAG']) in [3,4]:
#                self._some_bad_data_files.append(filename)
            self.status_dict['Total Obs'] = len(self.ds['DATETIME'])
            # this is annoying but it didn't want to unpack single tuples...
            values, counts = np.unique(self.ds['QC_FLAG'].values,return_counts=True)
            if len(values)>1:
                for values, counts in zip(values,counts):
                    self.status_dict[f'QC={values}'] = counts
            else:
                self.status_dict[f'QC={values[0]}'] = counts[0]
        else:
            self.status_dict.update({'Failed':'yes','Failure Mode':'No Good Data (all QC Flags = 4)'})
            #self._failed_files.append(f'{filename}: No Good Data (all QC Flags = 4)')

    def run(self):
        # set all readers/preprocessors
        self.set_cycle(cycle_dt)
        self._set_all_classes()
        # load metadata common for all files
        self.fisher_metadata = self.metareader(metafile = self.metafile, gear_class = self.gear_class).run()
        self._set_filelist()
        # initialize status files
        self._status_data = {}

        # apply qc
        for filename in self.files_to_qc:
            self.status_dict = {}
            try:
                self.ds = self.datareader(filename = filename).run()
                self.ds = self.preprocessor(self.ds,self.fisher_metadata,filename).run()
                self.status_dict.update(self.ds.attrs)
                if not self.ds.attrs['Gear Class'] == 'unknown':
                    self._processed_classified_gear(filename)
                else:
                    self.status_dict.update({'Failed':'yes','Failure Mode':'Gear Class Unknown'})
                    #self._failed_files.append(f'{filename}: Gear Class Unknown')
            except Exception as exc:
                self.status_dict.update({'Failed':'yes','Failure Mode':'QC Wrapper Error'})
                #self._failed_files.append(f'{filename}: QC Wrapper Error')
                self.logger.error('Could not qc data from {}. Traceback: {}'.format(filename, exc))
                continue
            try:
                self.status_dict = {k: self.status_dict[k] for k in self.status_dict_keys if k in self.status_dict}
                self._status_data[filename] = self.status_dict
            except Exception:
                self.logger.error(f'Could not append status info for {filename}')
                continue
        self._save_status_data()
#        return(self._saved_files,self._failed_files)
