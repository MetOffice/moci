#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

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
    CYLC_TASK_LOG_ROOT

  Suite specific environment:
    MODELBASIS
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


class AtmosPostProc(control.RunPostProc):
    '''
    Methods and properties specific to the UM Atmosphere
    post processing application.
    '''
    def __init__(self, input_nl='atmospp.nl'):
        '''
        Initialise UM Atmosphere Postprocessing:
            Import namelists: atmospp, archiving, delete_sc
            Import required environment: CYLC_SUITE_WORK_DIR, MODELBASIS
            Check WORK and SHARE directories exist
            Determine dumpname for final cycle: archived but not deleted
        '''
        self.naml = nlist.loadNamelist(input_nl)
        self.convpp_streams = self._convpp_streams
        if self.runpp:

            self.envars = utils.loadEnv('CYLC_SUITE_WORK_DIR',
                                        'MODELBASIS')
            self.share = self._directory(self.naml.atmospp.share_directory,
                                         'ATMOS SHARE')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)
            self.work = self._directory(self._work, 'ATMOS WORK')

            self.ff_pattern = r'^{}a\.[pm][{{}}]'.format(self.suite.prefix) + \
                r'\d{{4}}(\d{{4}}|\w{{3}})(_\d{{2}})?(\.pp)?(\.arch)?$'

            if self.suite.finalcycle:
                dumpdate = utils.add_period_to_date(self.suite.cycledt,
                                                    self.suite.cycleperiod)
                self.final_dumpname = self.dumpname(dumpdate)
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
        return OrderedDict([('do_archive', self.naml.archiving.archive_switch),
                            ('do_delete', self.naml.delete_sc.del_switch),
                            ('finalcycle_archive',
                             self.naml.archiving.archive_switch and
                             self.suite.finalcycle),
                            ('finalise_debug', self.naml.atmospp.debug)])

    @property
    def _work(self):
        ''' Work directory - Contains unprocessed .arch files'''
        return os.path.join(self.envars.CYLC_SUITE_WORK_DIR,
                            self.suite.envars.CYLC_TASK_CYCLE_POINT,
                            self.suite.umtask)

    @property
    def streams(self):
        '''
        Returns a regular expression for the fieldsfile
        instantaneous streams to process'''
        if isinstance(self.naml.archiving.process_streams, str):
            streams = self.naml.archiving.process_streams
        else:
            streams = '1-9a-ln-rt-xz'
        return streams

    @property
    def means(self):
        'Returns a regular expression for the fieldsfile means to process'
        if isinstance(self.naml.archiving.process_means, str):
            means = self.naml.archiving.process_means
        else:
            means = 'msy'
        return means

    @property
    def _convpp_streams(self):
        '''
        Calculate the regular expression required to find files
        which should be converted to pp format
        '''
        fstreams = self.naml.archiving.archive_as_fieldsfiles
        if fstreams:
            if isinstance(fstreams, list):
                fstreams = '^'.join(fstreams)
            convpp = '^' + fstreams
        else:
            convpp = 'a-z1-9'
        return convpp

    def dumpname(self, dumpdate=None):
        ''' Returns the dump name to be archived and/or deleted'''
        if not dumpdate:
            dumpdate = self.suite.cycledt
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
                        self.naml.atmospp, fnfull, log_file,
                        self.suite.envars.CYLC_TASK_LOG_ROOT
                    ):
                    arch_dumps.append(fname)
            else:
                # Dump file was probably archived by a previous instance
                # of the app at this cycle
                pass

        return arch_dumps

    @timer.run_timer
    def pp_to_archive(self, log_file, finalcycle):
        '''Returns a list of [fields|pp]files to archive'''
        arch_pp = []
        all_ppstreams = self.streams + self.means
        if self.naml.archiving.archive_pp and all_ppstreams:
            datadir = self.share if finalcycle else self.work
            suffix = '' if finalcycle else '.arch'
            patt = self.ff_pattern.format(all_ppstreams)
            ppfiles = housekeeping.get_marked_files(datadir, patt, suffix)
        else:
            ppfiles = []

        for fname in ppfiles:
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                # Header verification required
                if validation.verify_header(
                        self.naml.atmospp, fnfull, log_file,
                        self.suite.envars.CYLC_TASK_LOG_ROOT
                    ):
                    # Convert fieldsfile to pp if required
                    convert_to_pp = re.match(
                        self.ff_pattern.format(self.convpp_streams), fname
                        )
                    if self.naml.archiving.convert_pp and convert_to_pp:
                        fnfull = housekeeping.convert_to_pp(
                            fnfull,
                            self.naml.atmospp.um_utils,
                            finalcycle is True
                            )
                    arch_pp.append(fnfull)

            elif os.path.exists(fnfull + '.pp'):
                # Tidy up any ppfiles left from previous failed archive attempts
                arch_pp.append(fnfull + '.pp')

            else:
                msg = 'File to be archived {} does not exist'.format(fnfull)
                utils.log_msg(msg, level='WARN')

        return arch_pp

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
        files_to_archive = self.pp_to_archive(log_file, finalcycle)
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
                convpp = self.naml.archiving.convert_pp and \
                    re.match(self.ff_pattern.format(self.convpp_streams),
                             os.path.basename(fname))
                rcode = self.suite.archive_file(fname, preproc=bool(convpp))
                if finalcycle and fname.endswith('pp') and rcode == 0:
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
        self.do_archive(finalcycle=True)

    @timer.run_timer
    def do_delete(self):
        '''Delete superseded or archived dumps and pp output'''
        archived = self.naml.archiving.archive_switch
        dump = pp_inst = pp_mean = None

        if archived:
            dump, pp_inst, pp_mean = \
                housekeeping.read_arch_logfile(self.suite.logfile,
                                               self.suite.prefix,
                                               self.streams,
                                               self.means)

        housekeeping.delete_dumps(self, dump, archived)
        housekeeping.delete_ppfiles(self, pp_inst, pp_mean, archived)


INSTANCE = ('atmospp.nl', AtmosPostProc)

if __name__ == '__main__':
    pass
