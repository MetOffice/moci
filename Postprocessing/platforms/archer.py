#!/usr/bin/env python
'''
**********************************************************************
Contribution by NCAS-CMS

**********************************************************************

NAME
    platforms/archer.py

DESCRIPTION
    ARCHER archiving system commands

ENVIRONMENT VARIABLES
  Standard Cylc/Rose environment:
    CYLC_SUITE_NAME
    CYLC_SUITE_OWNER
    CYLC_TASK_CYCLE_POINT
    CYLC_TASK_NAME
    CYLC_TASK_TRY_NUMBER

  Suite specific environment:

  External environment:

'''
import os

import utils
import timer

@timer.run_timer
def archive_to_rdf(filename, sourcedir, nlist):
    '''Assemble the dictionary of variables required to archive'''
    cmd = {
        'CURRENT_RQST_NAME':   filename,
        'DATAM':               sourcedir,
        'RUNID':               nlist.archive_name,
        'ARCHIVE_ROOT':        nlist.archive_root_path
        }

    arch_instance = _Archer(cmd)
    return arch_instance.put_data()


class _Archer(object):
    """
    Compile and run archiving commands for ARCHER.
    """

    def __init__(self, comms):
        self._rqst_name = comms['CURRENT_RQST_NAME']
        self._suite_id = comms['RUNID']
        self._sourcedir = comms['DATAM']

        if comms['ARCHIVE_ROOT']  == os.environ['ROSE_DATAC']:
            # Data staged to ROSE_DATAC so no need to append
            # suite_name & cycle point
            self._archivedir = comms['ARCHIVE_ROOT']
        else:
            # Data staged elsewhere - add suite name and cycle point
            # to achive dir
            self._archivedir = os.path.join(
                comms['ARCHIVE_ROOT'],
                self._suite_id,
                os.environ['CYLC_TASK_CYCLE_POINT']
            )

        # Create archive directory for this cycle
        if not os.path.exists(self._archivedir):
            utils.create_dir(self._archivedir)

    def put_data(self):
        '''Archive the data to the RDF'''
        archivedir = self._archivedir

        crn = self._rqst_name
        crn = os.path.expandvars(crn)

        # Because of full path, need to get the filename at the end
        crn = os.path.join(self._sourcedir, crn)

        if os.path.exists(crn):
            msg = 'Archiving {} to {}'.format(crn, archivedir)
            utils.log_msg(msg, level='INFO')

            mv_cmd = 'mv {} {}'.format(crn, archivedir)
            utils.log_msg('RSH Running command: {}'.format(mv_cmd))
            ret_code, output = utils.exec_subproc(mv_cmd)
            if ret_code != 0:
                msg='Failed to move file: {}\nError={}\n{}'.\
                    format(crn, ret_code, output)
                ret_code = 13

        else:
            msg = 'archer.py: No archiving done. ' \
                'Path/file does not exist:' + str(crn)
            msg += '\n -> Failed to copy ' + str(crn) + 'to' + archivedir
            utils.log_msg(msg, level='ERROR')
            ret_code = 99

        put_rtncode = {
            0:  'Archer: Archiving OK. (ReturnCode=0)',
            13: 'Archive Error: Failed to copy file to staging area '
                '(ReturnCode=13)',
            99: 'System Error: File does not exist '
                '(ReturnCode=99)',
        }

        if ret_code == 0:
            utils.log_msg(put_rtncode[0])
            msg = '{} copied to staging area {}'.format(crn, archivedir)
            level = 'INFO'
        elif ret_code == 13:
            utils.log_msg(put_rtncode[13])
            msg = '{} was NOT staged - Move failed'.format(crn)
            level = 'WARN'
        else:
            msg = 'archer.py: Unknown Error - Return Code =' + str(ret_code)
            level = 'WARN'
        utils.log_msg(msg, level)

        return ret_code

class ArcherArch(object):
    '''Default namelist for Archer archiving'''
    archive_name = os.environ['CYLC_SUITE_NAME']
    archive_root_path = ''

NAMELISTS = {'archer_arch': ArcherArch}

if __name__ == '__main__':
    pass
