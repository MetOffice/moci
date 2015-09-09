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
    suite.py

DESCRIPTION
    Class definition for SuiteEnvironment - holds model independent
    properties and methods

ENVIRONMENT VARIABLES
  Standard Cylc environment:
    CYLC_TASK_LOG_ROOT
    CYLC_TASK_CYCLE_POINT
    CYLC_TASK_CYCLE_TIME (Pre-Cylc 6.0 only)

  Suite specific environment:
    ARCHIVE FINAL - Suite defined: Logical to indicate final cycle
                    -> Default: False
    END_CYCLE_TIME (Pre-Cylc 6.0 only) - Suite defined
                    -> Default: False
'''
import re
import os

import nlist
import utils


class SuiteEnvironment(object):
    '''Object to hold model independent aspects of the post processing app'''
    def __init__(self, sourcedir, input_nl='atmospp.nl'):
        self.nl = nlist.loadNamelist(input_nl).suitegen
        self.envars = utils.loadEnv('CYLC_TASK_LOG_ROOT')

        try:
            # Cylc6.0 ->
            self.envars = utils.loadEnv('CYLC_TASK_CYCLE_POINT',
                                        append=self.envars)
            self.cylc6 = True
        except Exception:
            # Pre-Cylc6.0
            self.envars = utils.loadEnv('CYLC_TASK_CYCLE_TIME',
                                        append=self.envars)
            self.cylc6 = False

        self.sourcedir = sourcedir

    @property
    def suitename(self):
        try:
            return self.nl.archive_set
        except AttributeError:
            utils.log_msg('Suitename not available - Cannnot archive', 3)

    @property
    def umtask(self):
        return self.nl.umtask_name

    @property
    def prefix(self):
        return self.nl.prefix

    @property
    def cycleperiod(self):
        return self.nl.cycleperiod

    @property
    def tasks_per_cycle(self):
        return self.nl.tasks_per_cycle

    @property
    def cyclestring(self):
        ''' Returns an array of strings: YYYY,MM,DD,mm,ss'''
        try:
            cyclestring = self._cyclestring
        except AttributeError:
            if self.cylc6:
                match = re.search('(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z',
                                  self.envars.CYLC_TASK_CYCLE_POINT)
            else:
                match = re.search('(\d{4})(\d{2})(\d{2})(\d{2})',
                                  self.envars.CYLC_TASK_CYCLE_TIME)
            if match:
                self._cyclestring = match.groups()
            else:
                utils.log_msg('Unable to determine cycletime', 5)

        return self._cyclestring

    @property
    def cycledt(self):
        return map(int, self.cyclestring)

    @property
    def finalcycle(self):
        try:
            finalcycle = self._finalcycle
        except AttributeError:
            if self.cylc6:
                try:
                    self.envars = utils.loadEnv('ARCHIVE_FINAL',
                                                append=self.envars)
                    finalcycle = ('true' in self.envars.ARCHIVE_FINAL.lower())
                except Exception:
                    finalcycle = False
            else:
                self.envars = utils.loadEnv('END_CYCLE_TIME',
                                            append=self.envars)
                endcycle = map(int,
                               re.search('(\d{4})(\d{2})(\d{2})(\d{2})',
                                         self.envars.END_CYCLE_TIME).groups())
                finalcycle = (self.cycledt == endcycle)
            self._finalcycle = finalcycle

        return finalcycle

    @property
    def logfile(self):
        '''Archiving log will be sent to the suite log directory'''
        return self.envars.CYLC_TASK_LOG_ROOT + '-archive.log'

    def __archive_command(self, filename):
        '''
        Executes the specific archiving system.
        Currently set up only for MOOSE
        '''
        rcode = None

        if self.nl.archive_command.lower() == 'moose':
            # MOOSE Archiving
            import moo
            cmd = {
                'CURRENT_RQST_ACTION': 'ARCHIVE',
                'CURRENT_RQST_NAME':   filename,
                'DATAM':               self.sourcedir,
                'RUNID':               self.suitename,
                'CATEGORY':            'UNCATEGORISED'
            }

            moose_arch_inst = moo.CommandExec()
            rcode = moose_arch_inst.execute(cmd)[filename]

        else:
            utils.log_msg('Archive command not yet implemented', 5)

        return rcode

    def archive_file(self, archfile, logfile=None, debug=False):
        '''Archive file and write to logfile'''
        if debug:
            utils.log_msg('Archiving: ' + archfile, 0)
            log_line = '{} WOULD BE ARCHIVED\n'.format(archfile)
            arch_rcode = 0
        else:
            arch_rcode = self.__archive_command(archfile)
            if arch_rcode == 0:
                log_line = '{} ARCHIVE OK\n'.format(archfile)
            else:
                log_line = '{} ARCHIVE FAILED. Archive process error\n'.\
                    format(archfile)
                logfile = self.logfile

        if not logfile:
            logfile = self.logfile

        try:
            logfile.write(log_line)
        except AttributeError:  # String, not file given.  Open new file
            action = 'a' if os.path.exists(logfile) else 'w'
            logfile = open(logfile, action)
            logfile.write(log_line)
            logfile.close()

        return arch_rcode


class suitePostProc(object):
    ''' Default namelist for model independent properties '''
    prefix = '$RUNID'
    umtask_name = 'atmos'
    tasks_per_cycle = 1
    cycleperiod = 0, 1, 0, 0, 0
    archive_command = 'Moose'
    archive_set = '$CYLC_SUITE_REG_NAME'

NAMELISTS = {'suitegen': suitePostProc}


if __name__ == '__main__':
    pass
