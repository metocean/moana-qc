import numpy as np
import xarray as xr
from ops_core.utils import import_pycallable, catch_exception


class QC_wrapper(object):
    '''Wrapper class for observational data quality control.  Incorporates transferring files from
    an incoming directory to a new directory.

    '''
    def __init__(self,
                outfile_ext = '',
                list_list = None,
                metafile = '/data/obs/mangopare/incoming/Fisherman_details/Trial_fisherman_database.csv',
                datareader = {},
                metareader = {},
                preprocessor = {},
                save_flags = False,
                convert_p_to_z = True,
                default_latitude = -40,
                startstring = "DateTime (UTC)",
                dateformat = '%Y%m%dT%H%M%S',
                gear_class = {'Bottom trawl':'mobile','Potting':'stationary','Long lining':'mobile','Trawling':'mobile'},
                logger = logging,
                **kwargs)

        self.outfile_ext = putfile_ext
        self.test_list = test_list
        self.metafile = metafile
        self.datareader_class = datafilereader
        self.metareader_class = metafilereader
        self.preprocessor_class = preprocessor
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.default_latitude = default_latitude
        self.startstring = startstring
        self.dateformat = dateformat
        self.gear_class = gear_class
        self._default_datareader_class = 'qc_readers.MangopareStandardReader'
        self._default_metareader_class = 'qc_readers.MangopareMetadataReader'
        self._default_preprocessor_class = 'qc_preprocess.PreProcessMangopare'
        self.logger = logging

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt
        self.basefile = tzstrftime(cycle_dt, self.basefile_tz, self.basefile)
        self.remote_dir = tzstrftime(cycle_dt, self.basefile_tz, self.remote_dir)
        self.local_dir = cycle_dt.strftime(self.local_dir)
        self.local_basefile = cycle_dt.strftime(self.local_basefile)
        self._proxy.set_cycle(cycle_dt)

    def _set_reader(self,filereader,_default_reader_class):
        klass = filereader.pop('class', self._default_reader_class)
        filereader = import_pycallable(klass)
        return(filereader)
        self.logger.info('Using file reader: %s ' % klass)

    def _set_all_readers(self):
        self.datareader = _set_reader(self.datareader_class,self._default_datareader_class)
        self.metareader = _set_reader(self.metareader_class,self._default_metareader_class)
        self.preprocessor = _set_reader(self.preprocessor_class,self._default_preprocessor_class)

    def _transfer(self, source=None, transfer=None,
                  default='msl_actions.transfer.base.LocalTransferBase'):
        source = source or self._success_files
        transfer = transfer or self.transfer
        return self._proxy(source, transfer, 'source', default)

    def convert_pressure_to_depth(self):
        '''
        Converts pressure to depth in the ocean either using the
        mean latitude of the observations or using a default_latitude
        '''
        if not np.isnan(np.nanmean(self.ds['LATITUDE'])):
            d_lat = np.nanmean(self.ds['LATITUDE'])
        else:
            d_lat = self.default_latitude
        depth = [sw.eos80.dpth(catch(lambda: float(z)),d_lat) for z in self.ds['PRESSURE']]
        self.ds['DEPTH'] = xr.Variable(dims = 'PRESSURE', data = depth, attrs={'units':'[m]','standard_name':'depth'})

    def run(self):
        # set all readers/preprocessors
        self._set_all_readers()
        # load metadata common for all files
        self.fisher_metadata = self.metareader(metafile = self.metafile).run()
        # apply qc
        for filename in self._success_files:
            try:
                self.ds = self.datareader(filename = filename).run()
                self.ds = self.preprocessor(self.ds,self.fisher_metadata)
    #            qc_apply()
            except:
                tb = catch_exception(exc)
                self.logger.error('Could not qc data from {}. Traceback: {}'.format(filename, tb))
                continue
            if self.convert_p_to_z:
                self.convert_pressure_to_depth()
