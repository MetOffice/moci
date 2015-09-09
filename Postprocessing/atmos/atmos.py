#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
(C) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
*****************************COPYRIGHT******************************
--------------------------------------------------------------------
 Code Owner: Please refer to the UM file CodeOwners.txt
 This file belongs in section: Rose scripts
--------------------------------------------------------------------
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
                            ('do_delete', self.nl.delete_sc.del_switch),
                            ('del_dot_arch', True)])

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
            self._share = self.nl.atmospp.share_directory
            utils.check_directory(self._share)
            return self._share

    def dumpname(self, dumpdate=None):
        if not dumpdate:
            dumpdate = self.suite.cycledt
        return '{0}a.da{1:0>4d}{2:0>2d}{3:0>2d}_{4:0>2d}'.\
            format(self.suite.prefix, *dumpdate)

    def get_marked_files(self):
        archfiles = []
        archdumps = []
        suffix = '.arch'
        # Multiple work directories required for Pre-CYLC-6.0 only
        for datadir in self.work:
            archfiles += utils.get_subset(datadir, r'{}$'.format(suffix))
            archdumps += utils.get_subset(datadir,
                                          r'[a-z]{{5}}a.da.*{}$'.format(suffix))

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
            utils.log_msg('Failed to open archive log file', 5)

        # Get files to archive
        pp_to_archive = self.get_marked_files() if \
            self.nl.archiving.archive_pp else []
        dumps_to_archive = validation.make_dump_name(self) if \
            self.nl.archiving.archive_dumps else []

        files_to_archive = []
        for fn in pp_to_archive + dumps_to_archive:
            # Perform the header verification on each file
            fn = os.path.join(self.share, fn)
            if os.path.exists(fn):
                if validation.verify_header(self.nl.atmospp, fn, log_file,
                                            self.suite.envars.CYLC_TASK_LOG_ROOT):
                    files_to_archive.append(fn)
            else:
                msg = 'File {} does not exist - cannot archive'.format(fn)
                utils.log_msg(msg, 3)
                logfile.write(fn + ' ARCHIVE FAILED. File does not exist\n')

        # Perform the archiving
        if files_to_archive:
            msg = 'Archiving the following files:\n'
            msg += '\n '.join(files_to_archive)
            utils.log_msg(msg)

            for fn in files_to_archive:
                self.suite.archive_file(fn, logfile=log_file,
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
                                               self.suite.prefix)

        housekeeping.delete_dumps(self, dump, archived)
        housekeeping.delete_ppfiles(self, pp_inst, pp_mean, archived)

    def del_dot_arch(self):
        for workdir in self.work:
            to_delete = utils.get_subset(workdir, '\.arch$')
            if to_delete:
                msg = 'Removing ".arch" from work directory:\n\t ' + workdir
                utils.log_msg(msg)
                utils.remove_files(to_delete, workdir)
            else:
                utils.log_msg(' -> Nothing to delete')

INSTANCE = ('atmospp.nl', AtmosPostProc)

if __name__ == '__main__':
    pass
