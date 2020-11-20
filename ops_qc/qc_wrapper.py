import qc_tests_df as qcdf 
import qc_tests_sd as qcds

class QC_wrapper(object):
    '''Wrapper class for observational data quality control.  Incorporates transferring files from
    an incoming directory to a new directory.
    
    '''
    def __init__(self, 
                outfile_ext = '',
                qc_tests = None,
                metafile = '/data/obs/mangopare/Trial_fishermen_database.csv',
                datareader = qc_readers.MangopareStandardReader,
                metareader = qc_readers.MangopareMetadataReader,
                preprocessor = qc_preprocess.PreProcessMangopare,
                save_flags = False,
                convert_p_to_z = True,
                test_order = False,
                default_latitude = -40,
                startstring = "DateTime (UTC)",
                dateformat = '%Y%m%dT%H%M%S',
                gear_class = {'Bottom trawl':'mobile','Potting':'stationary','Long lining':'mobile','Trawling':'mobile'},
                logger = logging,
                **kwargs)

        self.outfile_ext = putfile_ext
        self.qc_tests = qc_tests
        self.metafile = metafile
        self.filereader = filereader
        self.preprocessor = preprocessor
        self.save_flags = save_flags
        self.convert_p_to_z = convert_p_to_z
        self.test_order = test_order
        self.default_latitude = default_latitude
        self.startstring = startstring
        self.dateformat = dateformat
        self.gear_class = gear_class
        self.logger = logging

    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt
        self.basefile = tzstrftime(cycle_dt, self.basefile_tz, self.basefile)
        self.remote_dir = tzstrftime(cycle_dt, self.basefile_tz, self.remote_dir)
        self.local_dir = cycle_dt.strftime(self.local_dir)
        self.local_basefile = cycle_dt.strftime(self.local_basefile)
        self._proxy.set_cycle(cycle_dt)

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
        # apply qc
        for filename in self._success_files:
            try:
                self.ds = self.datareader(filename = filename).run()
                self.ds = self.preprocess(self.ds)
                qc_apply()
            except:
                tb = catch_exception(exc)
                self.logger.error('Could not qc data from {}. Traceback: {}'.format(filename, tb))
                continue
            if self.convert_p_to_z:
                self.convert_pressure_to_depth()