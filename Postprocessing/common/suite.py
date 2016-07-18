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

import utils


class SuiteEnvironment(object):
    '''Object to hold model independent aspects of the post processing app'''
    def __init__(self, sourcedir, input_nl='atmospp.nl'):
        from nlist import loadNamelist
        try:
            self.nl = loadNamelist(input_nl).suitegen
        except AttributeError:
            msg = 'SuiteEnvironment: Failed to load ' \
                '&suitegen namelist from namelist file: ' + input_nl
            utils.log_msg(msg, level=5)

        if self.nl.archive_command.lower() == 'moose':
            try:
                self.nl_arch = loadNamelist(input_nl).moose_arch
            except AttributeError:
                msg = 'SuiteEnvironment: Failed to load ' \
                    '&moose_arch namelist from namelist file: ' + input_nl
                utils.log_msg(msg, level=5)

        self.envars = utils.loadEnv('CYLC_TASK_LOG_ROOT')

        self.envars = utils.loadEnv('CYLC_TASK_CYCLE_POINT',
                                    'CYLC_CYCLING_MODE',
                                    'CYCLEPOINT_OVERRIDE',
                                    append=self.envars)
        if hasattr(self.envars, 'CYLC_TASK_CYCLE_POINT'):
            self.cylc6 = True
        else:
            # Pre-Cylc6.0
            self.envars = utils.loadEnv('CYLC_TASK_CYCLE_TIME',
                                        append=self.envars)
            self.cylc6 = False

        self.sourcedir = sourcedir
        self.archiveOK = True

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
                try:
                    # Required for Single Cycle suites
                    cyclepoint = self.envars.CYCLEPOINT_OVERRIDE
                except AttributeError:
                    cyclepoint = self.envars.CYLC_TASK_CYCLE_POINT
                match = re.search('(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z',
                                  cyclepoint)
            else:
                match = re.search('(\d{4})(\d{2})(\d{2})(\d{2})',
                                  self.envars.CYLC_TASK_CYCLE_TIME)
            if match:
                self._cyclestring = match.groups()
            else:
                utils.log_msg('Unable to determine cycletime', level=5)

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
                self.envars = utils.loadEnv('ARCHIVE_FINAL',
                                            append=self.envars)
                try:
                    finalcycle = ('true' in self.envars.ARCHIVE_FINAL.lower())
                except AttributeError:
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

    def monthlength(self, month):
        '''Returns length of given month in days - calendar dependent'''
        days_per_month = {
            '360day': [None,] + [30,]*12,
            '365day': [None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
            'gregorian': [None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
            # "integer" required for rose-stem testing mode only - assumes 360day test
            'integer': [None,] + [30,]*12,
            }

        date = self.cycledt
        if date[0] % 4 == 0 and (date[0] % 100 != 0 or date[0] % 400 == 0):
            days_per_month['gregorian'][2] = 29

        try:
            return days_per_month[self.envars.CYLC_CYCLING_MODE][int(month)]
        except KeyError:
            msg = 'Calendar not recognised: ' + self.envars.CYLC_CYCLING_MODE
            utils.log_msg('SuiteEnvironment: ' + msg, level=5)

    def __archive_command(self, filename, preproc):
        '''
        Executes the specific archiving system.
        Currently set up only for MOOSE
        '''
        rcode = None

        if self.nl.archive_command.lower() == 'moose':
            # MOOSE Archiving
            import moo
            rcode = moo.archive_to_moose(filename, self.sourcedir,
                                         self.nl_arch, preproc)
        else:
            utils.log_msg('Archive command not yet implemented', level=5)

        return rcode

    def archive_file(self, archfile, logfile=None, preproc=False, debug=False):
        '''Archive file and write to logfile'''
        if debug:
            utils.log_msg('Archiving: ' + archfile, 0)
            log_line = '{} WOULD BE ARCHIVED\n'.format(archfile)
            arch_rcode = 0
        else:
            arch_rcode = self.__archive_command(archfile, preproc)
            if arch_rcode == 0:
                log_line = '{} ARCHIVE OK\n'.format(archfile)
            elif self.nl.archive_command.lower() == 'moose' and \
                    arch_rcode == 11:
                log_line = '{} FILE NOT ARCHIVED. File contains no fields\n'.\
                    format(archfile)
            else:
                log_line = '{} ARCHIVE FAILED. Archive process error\n'.\
                    format(archfile)
                self.archiveOK = False

        if not logfile:
            logfile = self.logfile

        try:
            logfile.write(log_line)
        except AttributeError:  # String, not file handle given.  Open new file
            action = 'a' if os.path.exists(logfile) else 'w'
            logfile = open(logfile, action)
            logfile.write(log_line)
            logfile.close()

        return arch_rcode

    def preprocess_file(self, cmd, filename, **kwargs):
        '''
        Invoke the appropriate pre-processing method prior to archiving
        '''
        icode = 0
        try:
            icode = getattr(self, 'preproc_' + cmd)(filename, **kwargs)
        except AttributeError:
            utils.log_msg('preprocess command not yet implemented: ' + cmd, 5)

        return icode

    def preproc_nccopy(self, filename, compression=0, chunking=None):
        '''
        Compression of standard NetCDF file output prior to archive
        '''
        tmpfile = filename + '.tmp'
        cmd_path = self.nl.nccopy_path
        if not os.path.basename(cmd_path) == 'nccopy':
            cmd_path = os.path.join(cmd_path, 'nccopy')

        # Compress the file (outputting to a new file)
        chunks = '-c {}'.format(','.join(chunking)) if chunking else ''
        compress_cmd = ' '.join([cmd_path, '-d', str(compression),
                                 chunks, filename, tmpfile])
        utils.log_msg('Compressing file using command: ' + compress_cmd)
        ret_code, output = utils.exec_subproc(compress_cmd)
        level = 2
        if ret_code == 0:
            msg = 'nccopy: Compression successful of file {}'.format(filename)
        else:
            msg = 'nccopy: Compression failed of file {}\n{}'.format(filename,
                                                                     output)
            level = 5

        # Move the compressed file so it overwrites the original
        try:
            os.rename(tmpfile, filename)
        except OSError:
            msg = msg + '\n -> Failed to rename compressed file'
            level = 5
        utils.log_msg(msg, level)

        return ret_code

    def preproc_ncdump(self, fname, **kwargs):
        '''
        Invoke NetCDF utility ncdump for reading file data
        Arguments shold be provided in the form of a dictionary
        '''

        cmd = self.nl.ncdump_path
        if not os.path.basename(cmd) == 'ncdump':
            cmd = os.path.join(cmd, 'ncdump')

        for key, val in kwargs.items():
            cmd = ' '.join([cmd, '-' + key, val])
        cmd = ' '.join([cmd, fname])

        utils.log_msg('ncdump: Getting file info: {}'.format(cmd), level=1)
        ret_code, output = utils.exec_subproc(cmd)
        level = 2
        if ret_code == 0:
            msg = 'ncdump: Command successful'
        else:
            msg = 'ncdump: Command failed:\n{}'.format(output)
            level = 5
        utils.log_msg(msg, level=level)

        return output


class SuitePostProc(object):
    ''' Default namelist for model independent properties '''
    prefix = os.environ['RUNID']
    umtask_name = 'atmos'
    tasks_per_cycle = 1
    cycleperiod = 0, 1, 0, 0, 0
    archive_command = 'Moose'
    nccopy_path = ''
    ncdump_path = ''


class TimerInfo(object):
    '''Default namelist for timer'''
    ltimer = False


NAMELISTS = {'suitegen': SuitePostProc, 'monitoring': TimerInfo}


if __name__ == '__main__':
    pass
