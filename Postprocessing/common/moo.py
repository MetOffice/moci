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
    common/moo.py

DESCRIPTION
    Moose archiving system commands

ENVIRONMENT VARIABLES
  Standard Cylc environment:
    CYLC_TASK_LOG_ROOT
    CYLC_TASK_CYCLE_POINT
    CYLC_TASK_CYCLE_TIME (Pre-Cylc 6.0 only)

  Suite specific environment:
    ARCHIVE FINAL - Suite defined: Logical to indicate final cycle
                    -> Default: False

  External environment:
    JOBTEMP
    UM_TMPDIR set using JOBTEMP if it exists
'''
import os
import re

import utils
import timer

@timer.run_timer
def archive_to_moose(filename, sourcedir, nlist, convertpp):
    '''Assemble the dictionary of variables required to archive'''
    cmd = {
        'CURRENT_RQST_ACTION': 'ARCHIVE',
        'CURRENT_RQST_NAME':   filename,
        'DATAM':               sourcedir,
        'RUNID':               nlist.archive_set,
        'CATEGORY':            'UNCATEGORISED',
        'DATACLASS':           nlist.dataclass,
        'ENSEMBLEID':          nlist.ensembleid,
        'MOOPATH':             nlist.moopath,
        'PROJECT':             nlist.mooproject,
        'CONVERTPP':           convertpp
        }

    rcode = CommandExec().execute(cmd)[filename]
    return rcode


class _Moose(object):
    """
    Compile and run Moose archiving commands.
    Intended as a private input class for a CommandExec instance.
    """
    def __init__(self, comms):
        self._rqst_name = comms['CURRENT_RQST_NAME']
        self._suite_id = comms['RUNID']
        self._sourcedir = comms['DATAM']
        try:
            self._cat = comms['CATEGORY']
        except KeyError:
            self._cat = 'UNCATEGORISED'
        self._class = comms['DATACLASS']
        self._ens_id = comms['ENSEMBLEID']
        self._moopath = comms['MOOPATH']
        self._project = comms['PROJECT']
        self.convertpp = comms['CONVERTPP']

        # Define the collection name
        runid, rqst = re.split('[._]', os.path.basename(self._rqst_name), 1)
        self._model_id = runid[-1]
        self._file_id = rqst
        self.fl_pp = False
        if not self.chkset():
            self.mkset()  # Create a set

    @property
    def dataset(self):
        '''Return the path to the Moose dataset'''
        return 'moose:' + self._class + "/" + self._suite_id

    def chkset(self):
        '''Test whether Moose set exists'''
        chkset_cmd = '{} test -sw {}'.format(
            os.path.join(self._moopath, 'moo'), self.dataset
            )
        ret_code, output = utils.exec_subproc(chkset_cmd, verbose=False)

        exist = True if output.strip() == 'true' else False
        if exist:
            utils.log_msg('chkset: Using existing Moose set', 1)
        return exist

    def mkset(self):
        '''Create Moose set'''
        mkset_cmd = os.path.join(self._moopath, 'moo') + ' mkset -v '
        if self._cat != 'UNCATEGORISED':
            mkset_cmd += '-c ' + self._cat + ' '
        if self._project:
            mkset_cmd += '-p ' + self._project + ' '
        mkset_cmd += self.dataset

        utils.log_msg('mkset command: ' + mkset_cmd)
        ret_code, output = utils.exec_subproc(mkset_cmd, verbose=False)

        level = 1
        if ret_code == 0:
            msg = 'mkset: Successfully created set: ' + self.dataset
        elif ret_code == 10:
            msg = 'mkset: Set already exists:' + self.dataset
        else:
            msg = 'mkset: System error (Error={})'.format(ret_code)
            msg += '\n\t Unable to create set:' + self.dataset
            level = 4
        utils.log_msg(msg, level)

    def _collection(self):
        """
        Create the file extension based on the three letters following
        the runid in the filename
        """
        ext = ''
        msg = ''
        model_id = self._model_id

        if model_id == 'a':  # Atmosphere output
            file_id = self._file_id[:2]
            if re.search('[mp][1-9|a-z]', file_id):
                if self.convertpp:
                    ext = '.pp'
                else:
                    ext = '.file'
            elif re.search('v[1-5|a-j|lmsvy]', file_id):
                ext = '.pp'
            elif re.search('n[1-9|a-m|s-z]', file_id):
                ext = '.nc.file'
            elif re.search('b[a-j|mxy]', file_id):
                ext = '.file'
            elif re.search('d[amsy]', file_id):
                ext = '.file'
            elif re.search('r[a-m|qstuvwxz]', file_id):
                ext = '.file'

        elif model_id in 'io':  # NEMO/CICE means and restart dumps
            # ultimately file_id needs to be reassigned as a 2char variable
            file_id = re.split('[._]', self._file_id)
            if re.match(r'\d+[hdmsy]', file_id[0]):
                ext = '.nc.file'
                file_id = 'n' + file_id[0][-1]
            elif 'restart' in file_id:
                ext = '.file'
                file_id = 'da'  # These are restart dumps - reassign ID
            elif 'trajectory' in file_id:
                ext = '.nc.file'
                file_id = 'ni'
            else:
                msg = 'moo.py - ocean/sea-ice file type not recognised: '
                utils.log_msg(msg + self._rqst_name, level=5)

        else:
            msg = 'moo.py - Model id "{}" in filename  not recognised.'.\
                format(model_id)
            msg += '\n -> Please contact crum@metoffice.gov.uk ' \
                'if your requirements are not being met by this script.'
            utils.log_msg(msg, 5)

        if ext == '.pp':
            self.fl_pp = True

        return model_id + file_id + ext

    def put_data(self):
        """ Archive the data using moose """
        collection_name = self._collection()
        crn = self._rqst_name
        if crn.startswith('$'):  # For $PREFIX$RUNID cases
            # Get the file extension
            runid, postfix = re.split('[._]', crn, 1)
            sep = crn[len(runid)]
            collection_name = os.environ['RUNID'] + sep + postfix
        crn = os.path.expandvars(crn)

        # Because of full path, need to get the filename at the end
        crn = os.path.join(self._sourcedir, crn)

        moo_cmd = os.path.join(self._moopath, 'moo') + ' put -f -vv '
        if self.fl_pp and not crn.endswith('.pp'):
            crn_pp = os.path.basename(crn) + '.pp'
            filepath = os.path.join(self.dataset, self._ens_id,
                                    collection_name, crn_pp)
            moo_cmd += '-c=umpp {} {}'.format(crn, filepath)
        else:
            filepath = os.path.join(self.dataset, self._ens_id,
                                    collection_name)
            moo_cmd += '{} {}'.format(crn, filepath)

        if os.path.exists(crn):
            try:
                jobtemp = os.environ['JOBTEMP']
                if jobtemp:
                    os.environ['UM_TMPDIR'] = jobtemp
                else:
                    msg = 'JOBTEMP not set: moo, convpp, ieee likely to fail'
                    utils.log_msg(msg, 3)

            except KeyError:
                pass

            utils.log_msg('The command to archive is: ' + moo_cmd)
            ret_code, output = utils.exec_subproc(moo_cmd)

        else:
            msg = 'moo.py: No archiving done. Path/file does not exist:' + crn
            msg += '\n -> The command to archive would have been:\n' + moo_cmd
            utils.log_msg(msg, 4)
            ret_code = 99

        put_rtncode = {
            0:  'Moose: Archiving OK. (ReturnCode=0)',
            2:  'Moose Error: user-error (see Moose docs). (ReturnCode=2)',
            3:  'Moose Error: error in Moose or its supporting systems '
                '(storage, database etc.). (ReturnCode=3)',
            4:  'Moose Error: error in an external system or utility. '
                '(ReturnCode=4)',
            11: 'Moose System Warning: Fieldsfile contained no fields '
                'and was therefore not archived (ReturnCode=11)',
            99: 'System Error: The archiving file does not exist '
                '(ReturnCode=99)',
            230: 'System Error: Archiving command failed - Failed to find VM '
                 '- Check network access to archive',
        }

        if ret_code == 0:
            utils.log_msg(put_rtncode[0])
            msg = '{} added to the {} collection'.format(crn, collection_name)
            level = 1
        elif ret_code == 11:
            utils.log_msg(put_rtncode[11])
            msg = '{} not added to the {} collection - it contains no fields'.\
                format(crn, collection_name)
            level = 3
        elif ret_code in put_rtncode:
            msg = 'moo.py: {} File: {}'.format(put_rtncode[ret_code], crn)
            level = 4
        else:
            msg = 'moo.py: Unknown Error - Return Code =' + str(ret_code)
            level = 4
        utils.log_msg(msg, level)

        return ret_code


class CommandExec(object):
    def archive(self, comms):
        """ Carry out the archiving """
        mooInstance = _Moose(comms)
        return mooInstance.put_data()

    def delete(self, fn, prior_code=None):
        """ Carry out the delete command """
        if prior_code in [None, 0, 11, 99]:
            try:
                os.remove(fn)
            except OSError:
                pass
            finally:
                utils.log_msg('moo.py: Deleting file: ' + fn, 1)
        else:
            utils.log_msg('moo.py: Not deleting un-archived file: ' + fn, 3)
        return 1 if os.path.exists(fn) else 0

    def execute(self, commands):
        ''' Run the archiving and deletion as required '''
        ret_code = {}
        if (commands['CURRENT_RQST_ACTION'] == "ARCHIVE"):
            ret_code[commands['CURRENT_RQST_NAME']] \
                = self.archive(commands)

        elif (commands['CURRENT_RQST_ACTION'] == "DELETE"):
            try:
                prior_code = ret_code[commands['CURRENT_RQST_NAME']]
            except KeyError:
                prior_code = None
            ret_code['DELETE'] = self.delete(commands['CURRENT_RQST_NAME'],
                                             prior_code)
        else:
            msg = 'moo.py: Neither ARCHIVE nor DELETE requested: '
            utils.log_msg(msg + commands['CURRENT_RQST_NAME'], 3)
            ret_code['NO ACTION'] = 0
        print("\n")  # for clarity in output file.

        return ret_code


class MooseArch(object):
    '''Default namelist for Moose archiving'''
    archive_set = os.environ['CYLC_SUITE_REG_NAME']
    dataclass = 'crum'
    ensembleid = ''
    moopath = ''
    mooproject = ''

NAMELISTS = {'moose_arch': MooseArch}

if __name__ == '__main__':
    pass
