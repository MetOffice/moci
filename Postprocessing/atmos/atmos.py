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


class AtmosPostProc(control.runPostProc):
    '''
    Methods and properties specific to the UM Atmosphere
    post processing application.
    '''
    def __init__(self, input_nl='atmospp.nl'):
        self.nl = nlist.loadNamelist(input_nl)
        self.convpp_streams = self._convpp_streams

        if self.runpp:
            self.suite = suite.SuiteEnvironment(self.share, input_nl)

            self.envars = utils.loadEnv('CYLC_SUITE_WORK_DIR',
                                        'CYLC_TASK_LOG_ROOT', 'MODELBASIS')
            utils.log_msg('ATMOS SHARE directory: ' + self.share)
            utils.log_msg('ATMOS WORK directory: ' + ', '.join(self.work))

            if self.suite.finalcycle:
                dumpdate = utils.add_period_to_date(self.suite.cycledt,
                                                    self.suite.cycleperiod)
                self.final_dumpname = self.dumpname(dumpdate)
            else:
                self.final_dumpname = None

    @property
    def runpp(self):
        return self.nl.atmospp.pp_run

    @property
    def methods(self):
        return OrderedDict([('do_archive', self.nl.archiving.archive_switch),
                            ('do_delete', self.nl.delete_sc.del_switch)])

    @property
    def work(self):
        try:
            return self._work
        except AttributeError:
            self._work = []
            s_work = self.envars.CYLC_SUITE_WORK_DIR
            if self.suite.cylc6:
                um_work = '{0}/{1}'.\
                    format(self.suite.envars.CYLC_TASK_CYCLE_POINT,
                           self.suite.umtask)
                self._work.append(os.path.join(s_work, um_work))
            else:  # Pre Cylc-6.0
                for i in range(self.suite.tasks_per_cycle):
                    um_work = '{0}_{1:0>2d}.{2}'.\
                        format(self.suite.umtask, i+1,
                               self.suite.envars.CYLC_TASK_CYCLE_TIME)
                    self._work.append(os.path.join(s_work, um_work))

            for datadir in self._work:
                utils.check_directory(datadir)
            return self._work

    @property
    def share(self):
        try:
            return self._share
        except AttributeError:
            self._share = utils.check_directory(self.nl.atmospp.
                                                share_directory)
            return self._share

    @property
    def streams(self):
        '''
        Returns a regular expression for the fieldsfile
        instantaneous streams to process'''
        if self.nl.archiving.process_streams:
            streams = self.nl.archiving.process_streams
        else:
            streams = '1-9a-lp-rt-xz'
        return streams

    @property
    def means(self):
        'Returns a regular expression for the fieldsfile means to process'
        if self.nl.archiving.process_means:
            means = self.nl.archiving.process_means
        else:
            means = 'msy'
        return means

    @property
    def _convpp_streams(self):
        '''
        Calculate the regular expression required to find files
        which should be converted to pp format
        '''
        fstreams = self.nl.archiving.archive_as_fieldsfiles
        if fstreams:
            if isinstance(fstreams, list):
                fstreams = '^'.join(fstreams)
            convpp = '^' + fstreams
        else:
            convpp = 'a-z1-9'
        return convpp

    def dumpname(self, dumpdate=None):
        if not dumpdate:
            dumpdate = self.suite.cycledt
        return '{0}a.da{1:0>4d}{2:0>2d}{3:0>2d}_{4:0>2d}'.\
            format(self.suite.prefix, *dumpdate)

    def get_marked_files(self):
        '''Returns a list of fieldsfiles marked as available for archiving'''
        archfiles = []
        archdumps = []
        suffix = '.arch'
        # Multiple work directories required for Pre-CYLC-6.0 only
        for datadir in self.work:
            archfiles += utils.get_subset(datadir, r'^{}a\.[pm][{}].*{}$'.\
                                              format(self.suite.prefix,
                                                     self.streams + self.means,
                                                     suffix))
            archdumps += utils.get_subset(
                datadir, r'^{}a\.da.*{}$'.format(self.suite.prefix, suffix))

        archpp = list(set(archfiles) - set(archdumps))
        return [pp[:-len(suffix)] for pp in archpp]

    def do_archive(self):
        '''
        Function to collate the files to archive and pass them to the
        MOOSE archiving script. Owing to the requirements for the pp files
        and dump files this function will consider them separately.
    '''
        # Open our log files
        action = 'a' if os.path.exists(self.suite.logfile) else 'w'
        try:
            log_file = open(self.suite.logfile, action)
        except IOError:
            utils.log_msg('Failed to open archive log file', level=5)

        # Get files to archive
        pp_to_archive = self.get_marked_files() if \
            self.nl.archiving.archive_pp else []
        dumps_to_archive = validation.make_dump_name(self) if \
            self.nl.archiving.archive_dumps else []
        convert_pattern = re.compile(r'^{}a.[pm][{}]\d{{4}}.*$'.
                                     format(self.suite.prefix,
                                            self.convpp_streams))

        files_to_archive = []
        for fname in pp_to_archive + dumps_to_archive:
            # Perform the header verification on each file
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                if validation.verify_header(self.nl.atmospp, fnfull, log_file,
                                            self.suite.envars.
                                            CYLC_TASK_LOG_ROOT):
                    if self.nl.archiving.convert_pp and \
                            convert_pattern.match(fname):
                        # Convert fieldsfiles to pp format
                        fnfull = housekeeping.convert_to_pp(
                            fnfull, self.share, self.nl.atmospp.um_utils
                            )
                    files_to_archive.append(fnfull)
                else:
                    self.suite.archiveOK = False

            elif os.path.exists(fnfull + '.pp'):
                # Tidy up any ppfiles left from previous failed archive attempts
                files_to_archive.append(fnfull + '.pp')

            else:
                msg = 'File {} does not exist - cannot archive'.format(fnfull)
                utils.log_msg(msg, level=3)
                msg = fnfull + ' FILE NOT ARCHIVED. File does not exist\n'
                log_file.write(msg)

        # Perform the archiving
        if files_to_archive:
            msg = 'Archiving the following files:\n'
            msg += '\n '.join(files_to_archive)
            utils.log_msg(msg)

            for fname in files_to_archive:
                if convert_pattern.match(os.path.basename(fname)):
                    convertpp = True
                else:
                    convertpp = False
                self.suite.archive_file(fname, logfile=log_file,
                                        preproc=convertpp,
                                        debug=self.nl.atmospp.debug)
        else:
            utils.log_msg(' -> Nothing to archive')

        log_file.close()

    def do_delete(self):
        archived = self.nl.archiving.archive_switch
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
