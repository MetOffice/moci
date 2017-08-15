#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    atmos.py

DESCRIPTION
    Atmosphere post processing application

ENVIRONMENT VARIABLES
  Standard Cylc environment:
    CYLC_SUITE_WORK_DIR
    CYLC_TASK_CYCLE_POINT
'''

import os
import re

from collections import OrderedDict

import control
import utils
import nlist
import validation
import housekeeping
import suite
import timer

from netcdf_filenames import NCF_TEMPLATE


class AtmosPostProc(control.RunPostProc):
    '''
    Methods and properties specific to the UM Atmosphere
    post processing application.
    '''
    def __init__(self, input_nl='atmospp.nl'):
        '''
        Initialise UM Atmosphere Postprocessing:
            Import namelists: atmospp, archiving, delete_sc
            Import required environment:
                CYLC_SUITE_WORK_DIR, CYLC_TASK_WORK_DIR
            Check WORK and SHARE directories exist
            Determine dumpname for final cycle: archived but not deleted
        '''
        self.naml = nlist.loadNamelist(input_nl)
        self.convpp_streams = self._convpp_streams
        self.netcdf_streams = self._netcdf_streams

        if self.runpp:
            self.share = self._directory(self.naml.atmospp.share_directory,
                                         'ATMOS SHARE')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)
            self.work = self._directory(self._work, 'ATMOS WORK')

            self.ff_pattern = r'^{}a\.[pm][{{}}]'.format(self.suite.prefix) + \
                r'\d{{4}}(\d{{4}}|\w{{3}})(_\d{{2}})?(\.pp)?(\.arch)?$'

            if self.suite.finalcycle is True:
                self.final_dumpname = self.dumpname(
                    dumpdate=self.suite.cyclepoint.endcycle['intlist']
                    )
            else:
                self.final_dumpname = None

            # Initialise debug mode - calling base class method
            self._debug_mode(debug=self.naml.atmospp.debug)

    @property
    def runpp(self):
        '''
        Logical - Run postprocessing for UM Atmosphere
        Set via the atmospp namelist
        '''
        return self.naml.atmospp.pp_run

    @property
    def methods(self):
        '''
        Returns a dictionary of methods available for this model to the
        main program
        '''
        return OrderedDict([('do_transform', self.naml.atmospp.convert_pp or
                             self.naml.atmospp.streams_to_netcdf),
                            ('do_archive', self.naml.archiving.archive_switch),
                            ('do_delete', self.naml.delete_sc.del_switch),
                            ('finalcycle_archive',
                             any([self.naml.archiving.archive_switch,
                                  self.naml.atmospp.convert_pp,
                                  self.naml.atmospp.streams_to_netcdf]) and
                             self.suite.finalcycle),
                            ('finalise_debug', self.naml.atmospp.debug)])

    @property
    def _work(self):
        ''' Work directory - Contains unprocessed .arch files'''
        cylc_work = utils.load_env('CYLC_SUITE_WORK_DIR', required=True)
        cylc_cycle = utils.load_env('CYLC_TASK_CYCLE_POINT', required=True)

        return os.path.join(cylc_work, cylc_cycle, self.suite.umtask)

    @property
    def streams(self):
        '''
        Returns a regular expression for the fieldsfile
        instantaneous streams to process'''
        if isinstance(self.naml.atmospp.process_streams, str):
            streams = self.naml.atmospp.process_streams
        else:
            streams = '1-9a-ln-rt-xz'
        return streams

    @property
    def means(self):
        'Returns a regular expression for the fieldsfile means to process'
        if isinstance(self.naml.atmospp.process_means, str):
            means = self.naml.atmospp.process_means
        else:
            means = 'msy'
        return means

    @property
    def _convpp_streams(self):
        '''
        Calculate the regular expression required to find files
        which should be converted to pp format
        '''
        fstreams = self.naml.atmospp.archive_as_fieldsfiles
        if fstreams:
            if isinstance(fstreams, list):
                fstreams = '^'.join([str(x) for x in fstreams])
            convpp = '^' + str(fstreams)
        else:
            convpp = 'a-z1-9'
        return convpp

    @property
    def archive_tstamps(self):
        '''
        Return a list of timestamps for dumps to archive, having
        removed blank strings.
        '''
        tstamps = self.naml.archiving.arch_timestamps
        if not isinstance(tstamps, list):
            tstamps = [tstamps]
        return [ts for ts in tstamps if ts]

    @property
    def _netcdf_streams(self):
        '''
        Calculate the regular expression required to find files
        which should be have fields extracted to netCDF format
        '''
        ncf_streams = self.naml.atmospp.streams_to_netcdf
        if isinstance(ncf_streams, list):
            ncf_streams = ''.join([str(x) for x in ncf_streams])
        return ncf_streams

    @property
    def netcdf_fields(self):
        '''
        Return a dictionary of field names or STASH codes
        with an associated descriptor.
        The namelist variable &atmospp.fields_to_netcdf
        should contain a list of pairs of <type str> such that
        len(fields) % 2 == 0:
            (field name or STASHcode, descriptor)

        The descriptor is to be used as the "custom" facet for the
        Met Office netCDF naming convention for netCDF diagnostic files.
        '''
        if self.netcdf_streams:
            fields = self.naml.atmospp.fields_to_netcdf
        else:
            fields = []

        if not isinstance(fields, list) or len(fields) % 2 != 0:
            msg = 'Incorrect format of &atmospp/fields_to_netcdf'
            msg += ' -> <field name>, <descriptor> pairs expected.'
            utils.log_msg(msg, level='WARN')
            fields = []

        return {key: fields[i+1] for i, key in enumerate(fields)
                if fields.index(key) % 2 == 0}

    def dumpname(self, dumpdate=None):
        '''
        Returns the dump name to be archived and/or deleted.
        Optional argument:
          dumpdate - List of <type int> values
                   - Default = current cyclepoint
        '''
        if dumpdate is None:
            dumpdate = self.suite.cyclepoint.startcycle['intlist']
        return '{0}a.da{1:0>4d}{2:0>2d}{3:0>2d}_{4:0>2d}'.\
            format(self.suite.prefix, *dumpdate)

    def dumps_to_archive(self, log_file):
        '''Returns a list of dump files to archive'''
        arch_dumps = []
        dump_files = validation.make_dump_name(self) if \
            self.naml.archiving.archive_dumps else []

        for fname in dump_files:
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                # Header verification required
                if validation.verify_header(
                        self.naml.atmospp, fnfull,
                        self.suite.envars['CYLC_TASK_LOG_ROOT'],
                        logfile=log_file
                    ):
                    arch_dumps.append(fname)
            else:
                # Dump file was probably archived by a previous instance
                # of the app at this cycle
                pass

        return arch_dumps

    @timer.run_timer
    def diags_to_process(self, finalcycle, log_file=None):
        '''
        Return a list of fields/pp files eligible to file transformation
        or archive.
        Filenames returned will always incude full path.
        '''
        datadir = self.share if finalcycle else self.work
        suffix = '' if finalcycle else '.arch'
        all_ppstreams = self.streams + self.means
        if all_ppstreams:
            patt = self.ff_pattern.format(self.streams + self.means)
            markedfiles = housekeeping.get_marked_files(datadir, patt, suffix)
        else:
            markedfiles = []

        process_files = []
        for fname in markedfiles:
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                if fnfull.endswith('.pp'):
                    # Header verifcation already complete
                    process_files.append(fnfull)
                elif validation.verify_header(
                        self.naml.atmospp, fnfull,
                        self.suite.envars['CYLC_TASK_LOG_ROOT'],
                        logfile=log_file
                    ):
                    # Header verification required
                    process_files.append(fnfull)
            elif os.path.exists(fnfull + '.pp'):
                # Collect any previously converted ppfiles
                process_files.append(fnfull + '.pp')
            else:
                msg = 'File for processing {} does not exist'.format(fnfull)
                utils.log_msg(msg, level='WARN')

        # Collect any previously created netCDF files
        ncfiles = utils.get_subset(
            self.share,
            NCF_TEMPLATE.format(P='atmos_{}a'.format(self.suite.prefix),
                                B=r'\d+[hdmsyx]',
                                S=r'\d{8}',
                                E=r'\d{8}',
                                C='.*') + '$'
            )
        process_files += [os.path.join(self.share, fn) for fn in ncfiles]

        return process_files

    @timer.run_timer
    def do_transform(self, finalcycle=False):
        '''
        Function to perform requested transformation of fieldsfiles.
        '''
        # Get files which are available to archive, and thus eligible
        # for transform operations.
        for fname in self.diags_to_process(finalcycle):
            # fname returned by diags_to_process always includes the full path
            basename = os.path.basename(fname)
            if self.naml.atmospp.convert_pp and not fname.endswith('.pp'):
                if re.match(self.ff_pattern.format(self.convpp_streams),
                            basename):
                    fname = housekeeping.convert_to_pp(
                        fname,
                        self.naml.atmospp.um_utils,
                        finalcycle is True
                        )

            if self.netcdf_streams and re.match(
                    self.ff_pattern.format(self.netcdf_streams), basename
                ):
                icode = housekeeping.extract_to_netcdf(
                    fname, self.netcdf_fields,
                    self.naml.atmospp.netcdf_filetype,
                    self.naml.atmospp.netcdf_compression
                    )
                if icode != 0:
                    msg = 'do_transform - Field extraction to netCDF failed'
                    utils.log_msg(msg, level='ERROR')

    @timer.run_timer
    def do_archive(self, finalcycle=False):
        '''
        Function to collate the files to archive and pass them to the
        archiving script.
        Optional argument: finalcycle=True when called from finalcycle_archive.
        '''
        # Open our log files
        action = 'a' if os.path.exists(self.suite.logfile) else 'w'
        try:
            log_file = open(self.suite.logfile, action)
        except IOError:
            utils.log_msg('Failed to open archive log file', level='FAIL')

        # Get files to archive
        files_to_archive = []
        if self.naml.archiving.archive_pp:
            files_to_archive += self.diags_to_process(finalcycle,
                                                      log_file=log_file)
            # Do not archive both fieldsfile and ppfile
            files_to_archive = [fn for fn in files_to_archive
                                if fn + '.pp' not in files_to_archive]
        if not finalcycle:
            # Dumps are archived by first call to do_archive during final cycle
            files_to_archive += self.dumps_to_archive(log_file)

        log_file.close()

        # Perform the archiving
        if files_to_archive:
            msg = 'Archiving the following files:\n'
            msg += '\n '.join(files_to_archive)
            utils.log_msg(msg)

            for fname in files_to_archive:
                # convpp should be True when the ffile is to be archived as pp
                convpp = re.match(self.ff_pattern.format(self.convpp_streams),
                                  os.path.basename(fname)) or \
                                  not self.naml.atmospp.convert_pp
                rcode = self.suite.archive_file(fname, preproc=bool(convpp))
                if finalcycle and rcode == 0 and fname[-3:] in ['.pp', '.nc']:
                    if utils.get_debugmode():
                        os.rename(fname, fname + '_ARCHIVED')
                    else:
                        utils.remove_files(fname)

        else:
            utils.log_msg(' -> Nothing to archive')

    @timer.run_timer
    def finalcycle_archive(self):
        '''
        Archive but do not delete potentially incomplete fieldsfiles left
        on disk at the completion of the final cycle.
        '''
        if self.naml.atmospp.convert_pp or self.netcdf_streams:
            self.do_transform(finalcycle=True)

        if self.naml.archiving.archive_switch:
            self.do_archive(finalcycle=True)

    @timer.run_timer
    def do_delete(self):
        '''Delete superseded or archived dumps and pp output'''
        archived = self.naml.archiving.archive_switch
        dump = pp_inst = pp_mean = ncfile = None

        if archived:
            dump, pp_inst, pp_mean, ncfile = \
                housekeeping.read_arch_logfile(self.suite.logfile,
                                               self.suite.prefix,
                                               self.streams,
                                               self.means,
                                               self.netcdf_streams)

        housekeeping.delete_dumps(self, dump, archived)
        housekeeping.delete_ppfiles(self, pp_inst, pp_mean, ncfile,
                                    archived)


INSTANCE = ('atmospp.nl', AtmosPostProc)

if __name__ == '__main__':
    pass
