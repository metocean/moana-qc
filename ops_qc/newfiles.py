import os
import glob
import datetime as dt
import logging


class ListIncomingFiles(object):
    """
    Compare a list of already transferred files to the newly modified files
    in /data_exchange.  Calculates the new files that should be processed
    by ops_qc.
    Inputs:
        cutoff: timedelta time backward from end_date
    """

    def __init__(
        self,
        newfile_dir,
        old_files_dirs,
        files_to_append=None,
        cutoff=7,
        file_format="*.csv",
        outfile=None,
        end_date=None,
        maxfiles=500,
        override_max_files=False,
        logger=logging,
        **kwargs,
    ):
        self.newfile_dir = newfile_dir
        self.old_files_dirs = (
            old_files_dirs if isinstance(old_files_dirs, list) else [
                                         old_files_dirs]
        )
        self.files_to_append = files_to_append
        self.cutoff = cutoff
        self.outfile = outfile
        self.end_date = end_date
        self.logger = logger
        self.file_format = file_format
        self.maxfiles = maxfiles
        self.override_max_files = override_max_files
        self.cycle_dt = dt.datetime.now()

#    def set_cycle(self, cycle_dt):
#        self.cycle_dt = cycle_dt
#        if self.outfile:
#            self.outfile = cycle_dt.strftime(self.outfile)

    def _set_times(self):
        if not self.end_date:
            self.end_date = self.cycle_dt
        self.start_date = self.end_date - dt.timedelta(self.cutoff)

    def _check_dirs(self):
        if not self.newfile_dir:
            self.logger.error("New file directory not specified.")
            raise Exception
        if not self.old_files_dirs:
            self.logger.error("Old file directory not specified.")
            raise Exception

    def _list_transferred_files(self):
        transferred_files = []
        for dirname in self.old_files_dirs:
            files_in_dir = glob.glob(
                os.path.join(dirname, self.file_format), recursive=True
            )
            transferred_files.extend(
                [os.path.basename(fname) for fname in files_in_dir]
            )
        return transferred_files

    def _list_incoming_files(self):
        incoming_files = []
        indir = os.path.join(self.newfile_dir, self.file_format)
        self.logger.info(f'Looking for new files in {indir}...')
        files_in_dir = glob.glob(indir, recursive=True)
        for filename in files_in_dir:
            filetime = dt.datetime.fromtimestamp(os.path.getmtime(filename))
            if (filetime > self.start_date) and (filetime <= self.end_date):
                incoming_files.append(filename)
        base_files = [os.path.basename(fname) for fname in incoming_files]
        self.logger.info(
            f'Found {len(files_in_dir)} files in incoming directory and {len(base_files)} recent files.')
        return (incoming_files, base_files)

    def _create_filelist(self, new_file_list):
        infiles, inbases = self._list_incoming_files()
        oldfiles = self._list_transferred_files()
        #new_file_list.extend(list(np.array(infiles)[~np.in1d(inbases, oldfiles)]))  #this method faster but having type issues (numpy)
        new_file_list.extend([filename for filebase, filename in zip(
            inbases, infiles) if filebase not in oldfiles])
        self.logger.info(
            f'Found {len(infiles)} incoming files, {len(oldfiles)} transferred files, and {len(new_file_list)} new files.')
        if self.files_to_append:
            self.files_to_append = (
                self.files_to_append
                if isinstance(self.files_to_append, list)
                else [self.files_to_append]
            )
            new_file_list.extend(self.files_to_append)
            if len(new_file_list) > 0:
                new_file_list = [str(file) for file in new_file_list]
        return new_file_list

    def run(self):
        try:
            new_file_list = []
            self._set_times()
            self._check_dirs()
            new_file_list = self._create_filelist(new_file_list)
            self.logger.info(f'New files: {new_file_list}')
            if self.outfile:
                with open(self.outfile, "w") as outfile:
                    outfile.write("\n".join(new_file_list))
            if (len(new_file_list) > self.maxfiles) and (not self.override_max_files):
                self.logger.error(
                    f'Too many files: list is {len(new_file_list)} elements long')
                raise Exception
            else:
                return {"source": new_file_list}
        except Exception as exc:
            self.logger.error(f"Could not calculate list of new files: {exc}")
            return {"source": []}
