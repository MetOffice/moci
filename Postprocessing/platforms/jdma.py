#!/usr/bin/env python
'''
**********************************************************************
Contribution by NCAS-CMS:

**********************************************************************

NAME
    platforms/jdma.py

DESCRIPTION
    Migrate transferred data to JASMIN Elastic Tape

ENVIRONMENT VARIABLES
  Standard Cylc/Rose environment:
    CYLC_TASK_CYCLE_POINT
'''
import glob
import os
import pwd
import re

import nlist
import timer
import utils

from jdma_client import jdma_lib
from jdma_client import jdma_common


class NotAGroupWorkspace(Exception):
    def __str__(self):
        if self.args:
            err = '{} is not a group workspace'.format(self.args[0])
        else:
            err = 'not a group workspace'
        return err


def get_user_login_name():
    'Return <type str> a user login name'
    return pwd.getpwuid(os.getuid()).pw_name


def get_gws_root_from_path(path):
    '''
    Return <type str> The top-level path to the containing GWS.
                      The path does not have to exist, but the GWS must do so.

    Arguments:
       path <type str> File path
    '''
    if path.startswith('/gws/'):
        depth = 4

    elif path.startswith('/group_workspaces/'):
        depth = 3

    else:
        raise NotAGroupWorkspace(path)

    elements = os.path.normpath(path).split('/')

    if len(elements) < depth:
        raise NotAGroupWorkspace(path)

    gws_path = os.path.join('/', *elements[:depth + 1])

    if not os.path.isdir(gws_path):
        raise NotAGroupWorkspace(path)

    return gws_path


class JDMAInterface():

    def __init__(self, workspace):
        username = get_user_login_name()
        self.username = username
        utils.log_msg('username: {}'.format(self.username), level='INFO')
        self.storage_type = 'elastictape'
        self.credentials = {}
        self.workspace = workspace

    def submit_migrate(self, path):
        '''
        Submit a jdma MIGRATE job.
         - label is the directory to be uploaded
         - workspace (used for storage allocation) matches the one
           on which the files are located

        Return <type str> the request id

        Arguments:
           path <type str>
        '''
        if not self.workspace:
            workspace = self._get_workspace(path)
        else:
            workspace = self.workspace

        utils.log_msg('workspace: {}'.format(workspace), level='INFO')

        batch_id = self._get_batch_id_for_path(path)

        if batch_id is not None:
            utils.log_msg(
                'Path {} has already been migrated (as batch ID: {})'
                .format(path, batch_id), level='ERROR'
            )

        cycle = os.path.basename(path)
        suite_id = os.path.basename(os.path.dirname(path))

        resp = jdma_lib.upload_files(
            self.username,
            filelist=[path],
            request_type='MIGRATE',
            storage=self.storage_type,
            label=os.path.join(suite_id, cycle),
            credentials=self.credentials,
            workspace=workspace)

        return self._resp_to_req_id(resp)

    @staticmethod
    def _resp_to_req_id(resp):
        '''
        Return <type tuple> The (request ID, batch ID) in the response
                            from JDMA.
                            If status code was not 200, raises an
                            exception with the error.

        Arguments:
            resp <type requests.Response>
                             HTTP response object from JDMA client
                             call to upload files
        '''
        try:
            fields = resp.json()
        except ValueError:
            utils.log_msg('Unparseable response from JDMA', level='ERROR')

        status_code = resp.status_code

        if status_code == 200:
            try:
                return (fields['request_id'], fields['batch_id'])
            except KeyError:
                utils.log_msg('No request ID in JDMA response', level='ERROR')

        elif 'error' in fields:
            utils.log_msg(
                'JDMA request failed with HTTP status code {} and message: {}'
                .format(status_code, fields['error']), level='ERROR'
            )
        else:
            utils.log_msg('JDMA request failed with HTTP status code {}'
                          .format(status_code), level='ERROR')

        return (None, None)

    @staticmethod
    def _get_workspace(path):
        '''
        Return <type str> The workspace whose allocation will be used
                          by the JDMA.
                          This would exclude any _vol<number> part of the
                          directory path.

        Arguments:
            path <type str> File path
        '''
        gws_root = get_gws_root_from_path(path)
        basename = os.path.basename(os.path.normpath(gws_root))
        return re.sub('_vol[0-9]+$', '', basename)

    def _get_batch_id_for_path(self, path, must_exist=False):
        '''
        Return <type int> Batch ID

        Arguments:
           path <type str> File path
           must_exist <type bool> Flag is True if the batch must exist on
                                  the storage at the given path
                                  OPTIONAL: Default=False

        '''
        bid = self._get_batch_id_for_path2(path)
        if bid is None and must_exist:
            utils.log_msg(
                'Could not find batch on storage for path {}'.format(path),
                level='ERROR'
            )
        return bid

    def _get_batch_id_for_path2(self, path):
        '''
        Return <type int> The batch with label=the supplied path
                          and whose location is 'ON_STORAGE'
        Return <type None> When no batch is found.
        Raise an Error if more than one batch is found.

        Arguments:
           path <type str> File path
        '''

        if not self.workspace:
            workspace = self._get_workspace(path)
        else:
            workspace = self.workspace

        utils.log_msg('workspace: {}'.format(workspace), level='INFO')

        resp = jdma_lib.get_batch(self.username,
                                  workspace=workspace,
                                  label=path)

        if resp.status_code != 200:
            if resp.status_code % 100 == 5:
                utils.log_msg(
                    ('JDMA responded with status code {} when checking '
                     'for existing batches. Assuming none found.\n').
                    format(resp.status_code), level='WARN')
            return None

        resp_dict = resp.json()

        if 'migrations' in resp_dict:
            batches = resp_dict['migrations']
        else:
            batches = [resp_dict]

        batch_ids = [batch['migration_id'] for batch in batches if
                     jdma_common.get_batch_stage(batch['stage'])=='ON_STORAGE']

        num_matches = len(batch_ids)

        rval = None
        if num_matches == 1:
             rval = batch_ids[0]
        elif num_matches > 1:
            utils.log_msg(
                'found more than one batch on storage for path {} (ids={})'
                .format(path, ','.join(map(str, batch_ids))), level='ERROR'
            )
        return rval


class Jasmin(object):
    '''Class defining methods relating to JASMIN archiving'''

    def __init__(self, input_nl='jasmin.nl'):
        load_nl = nlist.load_namelist(input_nl)
        try:
            nl_arch = load_nl.archer_arch
        except AttributeError:
            msg = 'Transfer: Failed to load &archer_arch ' \
                'namelist from namelist file: ' + input_nl
            utils.log_msg(msg, level='FAIL')

        try:
            nl_transfer = load_nl.pptransfer
        except AttributeError:
            msg = 'Transfer: Failed to load &pptransfer ' \
                'namelist from namelist file: ' + input_nl
            utils.log_msg(msg, level='FAIL')

        try:
            nl_jasmin = load_nl.jasmin_arch
        except AttributeError:
            msg = 'Transfer: Failed to load &jasmin_arch ' \
                'namelist from namelist file: ' + input_nl
            utils.log_msg(msg, level='FAIL')

        self._suite_name = nl_arch.archive_name
        self._transfer_dir = os.path.join(
            nl_transfer.transfer_dir,
            self._suite_name,
            os.environ['CYLC_TASK_CYCLE_POINT']
        )

        self._jasmin_copy = nl_jasmin.jasmin_copy
        if self._jasmin_copy:
            self._copy_target = nl_jasmin.copy_target
            self._copy_streams = nl_jasmin.copy_streams

        self._default_workspace = nl_jasmin.default_workspace

        if self._default_workspace:
            self._workspace = None
        else:
            self._workspace = nl_jasmin.workspace

    @timer.run_timer
    def copy_streams(self):
        '''
        Copy subset of pp streams to GWS for examination.
        '''
        if not self._jasmin_copy:
            # copy_streams switched off
            return

        # Check there are some streams specified
        if not self._copy_streams:
            utils.log_msg('No streams specified to copy.', level='WARN')
            return

        # Work out files to copy
        pattern = '{}/*p[{}]*'.format(
            self._transfer_dir,
            ''.join([str(s) for s in self._copy_streams])
        )
        files = glob.glob(pattern)

        if len(files) == 0:
            utils.log_msg('No files found to copy.', level='WARN')
            return

        msg = 'Files to copy: {}'.format(files)
        utils.log_msg(msg, level='INFO')

        # Check base target directory exists
        if not os.path.isdir(self._copy_target):
            msg = 'Target directory does not exist: {}'.format(self._copy_target)
            utils.log_msg(msg, level='ERROR')
            return

        # If needed, create target directory with suite name
        target_dir = '{}/{}'.format(self._copy_target, self._suite_name)
        if not os.path.isdir(target_dir):
            mkdir_cmd = 'mkdir {}'.format(target_dir)
            ret_code, _ = utils.exec_subproc(mkdir_cmd)

            if ret_code == 0:
                msg = 'Made directory {}'.format(target_dir)
                utils.log_msg(msg, level='INFO')
            else:
                msg = 'Failed to make directory {}'.format(target_dir)
                utils.log_msg(msg, level='ERROR')
                return

        # Do the copy
        copy_cmd = 'cp {} {}'.format(' '.join([str(f) for f in files]), target_dir)
        ret_code, _ = utils.exec_subproc(copy_cmd)

        if ret_code == 0:
            msg = 'Successfully copied files to {}'.format(target_dir)
            utils.log_msg(msg, level='INFO')
        else:
            utils.log_msg('Failed to copy files', level='ERROR')

    @timer.run_timer
    def jdma_migrate(self):
        '''Initiate JDMA migration'''
        utils.log_msg('Migrating {} to Elastic Tape'.format(self._transfer_dir))

        jdma_inst = JDMAInterface(self._workspace)
        req_id, batch_id = jdma_inst.submit_migrate(self._transfer_dir)

        utils.log_msg('JDMA Request id: {}'.format(req_id), level='INFO')
        utils.log_msg('JDMA Batch id: {}'.format(batch_id), level='INFO')


def main():
    '''
    Main function:

    '''
    timer.initialise_timer()

    jasmin = Jasmin()

    # Copy subset of streams
    jasmin.copy_streams()

    # Migrate data to Elastic Tape
    jasmin.jdma_migrate()

    timer.finalise_timer()


class JasminArch(object):
    '''Default namelist for JASMIN Archiving'''
    default_workspace = True
    workspace = None
    jasmin_copy = False
    copy_streams = ''
    copy_target = ''

NAMELISTS = {'jasmin_arch': JasminArch}


if __name__ == '__main__':
    main()
