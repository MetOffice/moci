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

  Suite specific environment:
    ARCHIVE FINAL - Suite defined: Logical to indicate final cycle
                    -> Default: False
'''
import re
import os

import timer
import utils


class SuiteEnvironment(object):
    '''Object to hold model independent aspects of the post processing app'''
    def __init__(self, sourcedir, input_nl='atmospp.nl'):
        from nlist import loadNamelist
        load_nl = loadNamelist(input_nl)
        try:
            self.naml = load_nl.suitegen
        except AttributeError:
            msg = 'SuiteEnvironment: Failed to load ' \
                '&suitegen namelist from namelist file: ' + input_nl
            utils.log_msg(msg, level='FAIL')

        if self.naml.archive_command.lower() == 'moose':
            try:
                self.nl_arch = load_nl.moose_arch
            except AttributeError:
                msg = 'SuiteEnvironment: Failed to load ' \
                    '&moose_arch namelist from namelist file: ' + input_nl
                utils.log_msg(msg, level='FAIL')

        self.envars = utils.loadEnv('CYLC_TASK_LOG_ROOT',
                                    'CYLC_TASK_CYCLE_POINT',
                                    'CYLC_SUITE_FINAL_CYCLE_POINT',
                                    'CYLC_CYCLING_MODE',
                                    'CYCLEPOINT_OVERRIDE',
                                    'FINALCYCLE_OVERRIDE')

        self.sourcedir = sourcedir
        self.cyclestring = utils.cyclestring()
        self.finalcycle = utils.finalcycle()

        # Monitoring attributes
        self.archive_ok = True

    @property
    def umtask(self):
        '''
        Returns the name of the app producing the data for postprocessing.
        Provided via &suitegen namelist
        '''
        return self.naml.umtask_name

    @property
    def prefix(self):
        '''Returns the filename prefix.  Provided via &suitegen namelist'''
        return self.naml.prefix

    @property
    def logfile(self):
        '''Archiving log will be sent to the suite log directory'''
        return self.envars.CYLC_TASK_LOG_ROOT + '-archive.log'

    @property
    def cycleperiod(self):
        '''Returns the cycling period for the suite.
        Provided via  &suitegen namelist
        '''
        return self.naml.cycleperiod

    @property
    def cycledt(self):
        '''
        Creates a representation of the current cycletime in integer format.
        Returns a list of integers: YYYY,MM,DD,mm,ss
        '''
        return map(int, self.cyclestring)

    @property
    def logfile(self):
        '''Archiving log will be sent to the suite log directory'''
        return self.envars.CYLC_TASK_LOG_ROOT + '-archive.log'

    def monthlength(self, month):
        '''Returns length of given month in days - calendar dependent'''
        days_per_month = {
            '360day': [None, ] + [30]*12,
            '365day': [None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
            'gregorian': [None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
            # "integer" required for rose-stem testing mode - assumes 360day
            'integer': [None, ] + [30, ]*12,
            }

        date = self.cycledt
        if date[0] % 4 == 0 and (date[0] % 100 != 0 or date[0] % 400 == 0):
            days_per_month['gregorian'][2] = 29

        try:
            return days_per_month[self.envars.CYLC_CYCLING_MODE][int(month)]
        except KeyError:
            msg = 'Calendar not recognised: ' + self.envars.CYLC_CYCLING_MODE
            utils.log_msg('SuiteEnvironment: ' + msg, level='FAIL')

    def _archive_command(self, filename, preproc):
        '''
        Executes the specific archiving system.
        Currently set up only for MOOSE
        '''
        rcode = None

        if self.naml.archive_command.lower() == 'moose':
            # MOOSE Archiving
            import moo
            rcode = moo.archive_to_moose(filename, self.prefix, self.sourcedir,
                                         self.nl_arch, preproc)
        else:
            utils.log_msg('Archive command not yet implemented', level='ERROR')

        return rcode

    def archive_file(self, archfile, logfile=None, preproc=False):
        '''Archive file and write to logfile'''
        log_line = os.path.basename(archfile)
        if utils.get_debugmode():
            utils.log_msg('Archiving: ' + archfile, level='DEBUG')
            log_line += ' WOULD BE ARCHIVED\n'
            arch_rcode = 0
        else:
            arch_rcode = self._archive_command(archfile, preproc)
            if arch_rcode == 0:
                log_line += ' ARCHIVE OK\n'
            elif self.naml.archive_command.lower() == 'moose' and \
                    arch_rcode == 11:
                log_line += ' FILE NOT ARCHIVED. File contains no fields\n'
                arch_rcode = 0
            else:
                log_line += ' ARCHIVE FAILED. Archive process error\n'
                self.archive_ok = False

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

    @timer.run_timer
    def preprocess_file(self, cmd, filename, **kwargs):
        '''
        Invoke the appropriate pre-processing method prior to archiving
        '''
        rtnval = 0
        try:
            rtnval = getattr(self, 'preproc_' + cmd)(filename, **kwargs)
        except AttributeError:
            utils.log_msg('preprocess command not yet implemented: ' + cmd,
                          level='ERROR')

        return rtnval

    @timer.run_timer
    def preproc_nccopy(self, filename, compression=0, chunking=None):
        '''
        Compression of standard netCDF file output prior to archive
        '''
        tmpfile = filename + '.tmp'
        cmd_path = self.naml.nccopy_path
        if not os.path.basename(cmd_path) == 'nccopy':
            cmd_path = os.path.join(cmd_path, 'nccopy')

        # Compress the file (outputting to a new file)
        chunks = '-c {}'.format(','.join(chunking)) if chunking else ''
        compress_cmd = ' '.join([cmd_path, '-d', str(compression),
                                 chunks, filename, tmpfile])
        utils.log_msg('Compressing file using command: ' + compress_cmd)
        ret_code, output = utils.exec_subproc(compress_cmd)
        level = 'OK'
        if ret_code == 0:
            msg = 'nccopy: Compression successful of file {}'.format(filename)
            # Move the compressed file so it overwrites the original
            try:
                os.rename(tmpfile, filename)
            except OSError:
                msg = msg + '\n -> Failed to rename compressed file'
                level = 'ERROR'
                ret_code = 99
        else:
            msg = 'nccopy: Compression failed of file {}\n{}'.format(filename,
                                                                     output)
            level = 'ERROR'

        utils.log_msg(msg, level=level)
        return ret_code

    @timer.run_timer
    def preproc_ncdump(self, fname, **kwargs):
        '''
        Invoke netCDF utility ncdump for reading file data
        Arguments should be provided in the form of a dictionary
        '''

        cmd = self.naml.ncdump_path
        if not os.path.basename(cmd) == 'ncdump':
            cmd = os.path.join(cmd, 'ncdump')

        for key, val in kwargs.items():
            cmd = ' '.join([cmd, '-' + key, val])
        cmd = ' '.join([cmd, fname])

        utils.log_msg('ncdump: Getting file info: {}'.format(cmd), level='INFO')
        ret_code, output = utils.exec_subproc(cmd)
        level = 'OK'
        if ret_code == 0:
            msg = 'ncdump: Command successful'
        else:
            msg = 'ncdump: Command failed:\n{}'.format(output)
            level = 'ERROR'
        utils.log_msg(msg, level=level)

        return output

    @timer.run_timer
    def preproc_ncrcat(self, infiles, **kwargs):
        '''
        Invoke netCDF utility ncrcat for concatenating records
        Arguments should be provided in the form of a dictionary
        '''
        try:
            outfile = kwargs['outfile']
            del kwargs['outfile']
        except KeyError:
            msg = 'ncrcat: Cannot continue - output filename not provided'
            utils.log_msg(msg, level='ERROR')

        cmd = self.naml.ncrcat_path
        if not os.path.basename(cmd) == 'ncrcat':
            cmd = os.path.join(cmd, 'ncrcat')

        for key, val in kwargs.items():
            cmd = ' '.join([cmd, '-' + key, val])
        cmd = '{} {} {}'.format(cmd, ' '.join(infiles), outfile)

        utils.log_msg('ncrcat: Concatenating files: {}'.format(cmd),
                      level='INFO')
        ret_code, output = utils.exec_subproc(cmd)
        level = 'OK'
        if ret_code == 0:
            msg = 'ncrcat: Command successful'
        else:
            msg = 'ncrcat: Command failed:\n{}'.format(output)
            level = 'ERROR'
        utils.log_msg(msg, level=level)

        return ret_code


class SuitePostProc(object):
    ''' Default namelist for model independent properties '''
    prefix = os.environ['RUNID']
    umtask_name = 'atmos'
    cycleperiod = 0, 1, 0, 0, 0
    archive_command = 'Moose'
    nccopy_path = ''
    ncdump_path = ''
    ncrcat_path = ''


class TimerInfo(object):
    '''Default namelist for timer'''
    ltimer = False


NAMELISTS = {'suitegen': SuitePostProc, 'monitoring': TimerInfo}


if __name__ == '__main__':
    pass
