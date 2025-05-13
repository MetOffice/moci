#!/usr/bin/env python
'''
**********************************************************************
Contribution by NCAS-CMS

**********************************************************************

NAME
    platforms/transfer.py

DESCRIPTION
    Transfer of archived files from one machine to another

ENVIRONMENT VARIABLES
  Standard Cylc/Rose environment:
    CYLC_TASK_CYCLE_POINT
'''
import glob
import os

import nlist
import timer
import utils


class Transfer(object):
    '''Transfer archived files to JASMIN'''

    def __init__(self, input_nl='pptransfer.nl'):
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

        self._suite_name = nl_arch.archive_name
        self._verify_chksums = nl_transfer.verify_chksums
        self._globus_cli = nl_transfer.globus_cli

        if self._globus_cli:
            self._globus_notify = nl_transfer.globus_notify
            self._globus_default_colls = nl_transfer.globus_default_colls

            if self._globus_default_colls:
                # ARCHER2
                self._globus_src_coll = '3e90d018-0d05-461a-bbaf-aab605283d21'
                # JASMIN
                self._globus_dst_coll = 'a2f53b7f-1b4e-4dce-9b7c-349ae760fee0'
            else:
                self._globus_src_coll = nl_transfer.globus_src_coll 
                self._globus_dst_coll = nl_transfer.globus_dst_coll 
        else:
            self._remote_host = nl_transfer.remote_host

        self._transfer_type = nl_transfer.transfer_type.lower()
        self._checksums = 'checksums'

        utils.log_msg('archive_root_path:  {}'.\
                      format(nl_arch.archive_root_path))

        if nl_arch.archive_root_path == os.environ['ROSE_DATAC']:
            # Data staged to ROSE_DATAC so no need to append
            # suite_name & cycle point
            self._archive_dir = nl_arch.archive_root_path
        else:
            # Data staged elsewhere - add suite name and cycle point to
            # achive dir
            self._archive_dir = os.path.join(
                nl_arch.archive_root_path,
                self._suite_name,
                os.environ['CYLC_TASK_CYCLE_POINT']
            )

        self._transfer_dir = os.path.join(nl_transfer.transfer_dir,
                                          self._suite_name,
                                          os.environ['CYLC_TASK_CYCLE_POINT'])

        if self._verify_chksums:
            self.tidy_up()


    def tidy_up(self):
        '''Tidy up old files after previous run of the transfer app for
           this cycle'''
        if self._transfer_type == 'push':
            if os.path.exists(self._archive_dir):
                # Archive directory exists. Tidy up before continuing
                self._clean_up_push()
            else:
                msg = 'Archive directory {} doesn\'t exist'. \
                    format(self._archive_dir)
                utils.log_msg(msg, level='ERROR')
        else:
            # Check remote archive directory exists
            cmd = 'ssh ' + self._remote_host + ' -n ls ' + self._archive_dir
            ret_code, _ = utils.exec_subproc(cmd, verbose=False)
            if ret_code == 0:
                # Archive directory exists. Tidy up before continuing
                self._clean_up_pull()
            elif ret_code == 2:
                msg = 'Remote archive directory {} doesn\'t exist'. \
                    format(self._archive_dir)
                utils.log_msg(msg, level='ERROR')


    def _clean_up_push(self):
        '''Clean up any previous run of the transfer app for this cycle'''
        checksum_file = os.path.join(self._archive_dir, self._checksums)
        try:
            os.remove(checksum_file)
        except OSError:
            pass
        finally:
            msg = 'Deleting old checksum file: {}'.format(checksum_file)
            utils.log_msg(msg, level='INFO')


    def _clean_up_pull(self):
        '''Clean up any previous run of the transfer app for this cycle'''
        checksum_file = os.path.join(self._archive_dir, self._checksums)
        cmd = 'ssh ' + self._remote_host + ' -n ls ' + checksum_file
        ret_code, _ = utils.exec_subproc(cmd, verbose=False)
        if ret_code == 0:
            # Checksum file exists on remote host. Remove it.
            cmd = 'ssh ' + self._remote_host + ' -n rm ' + checksum_file
            ret_code, _ = utils.exec_subproc(cmd, verbose=False)
            if ret_code != 0:
                msg = 'Problem removing checksum file on remote host'
                utils.log_msg(msg, level='WARN')
        elif ret_code != 2:
            # Exclude ret_code=2 - this indicates the file doesn't exist on
            # the remote host..
            msg = 'Problem checking existence of checksum files on ' \
                'remote host'
            utils.log_msg(msg, level='WARN')


    @timer.run_timer
    def _generate_checksums(self):
        '''Generate checksums for files to be transferred.  This is the
        contents of cycle archive directory.'''
        if self._transfer_type == 'push':
            # Pushing files
            files_to_archive = glob.glob(self._archive_dir + '/*')
            # Strip off pathnames
            files_to_archive = [os.path.basename(f) for f in files_to_archive]

            cmd = (['md5sum'] + files_to_archive)
            ret_code, output = utils.exec_subproc(cmd,
                                                  verbose=False,
                                                  cwd=self._archive_dir)
            with open(os.path.join(self._archive_dir,
                                   self._checksums), 'w') as csfh:
                csfh.write(output)
        else:
            # Pulling files
            # Login to archive host, cd to archive directory and run md5sum
            cmd = (['ssh', '-oBatchMode=yes', self._remote_host, '-n', 'cd',
                    self._archive_dir, ';', 'md5sum', '*', '>',
                    self._checksums])
            workdir = os.getcwd()
            ret_code, _ = utils.exec_subproc(cmd, verbose=False, cwd=workdir)

        if ret_code != 0:
            utils.log_msg('Failed to generate checksums.', level='WARN')

        return ret_code == 0


    @timer.run_timer
    def _do_verify_checksums(self):
        '''Verify the checksums of transferred files. Checksum file was copied
        to transfer host along with the data files'''
        utils.log_msg('Verifying checksums...', level='INFO')

        if self._transfer_type == 'push':
            # Pushing files
            # Login to transfer host, cd to transfer directory and run md5sum
            cmd = (['ssh', '-oBatchMode=yes', self._remote_host, '-n', 'cd',
                    self._transfer_dir, ';', 'md5sum', '-c',
                    self._checksums])
            workdir = os.getcwd()
        else:
            # Pulling files
            cmd = 'md5sum -c ' + self._checksums
            workdir = self._transfer_dir

        ret_code, _ = utils.exec_subproc(cmd, cwd=workdir)

        if ret_code == 0:
            utils.log_msg('Checksum verification succeeded.', level='OK')
        else:
            utils.log_msg('Checksum verification failed.', level='ERROR')

        return ret_code == 0

    @timer.run_timer
    def _get_data_size(self):
        '''Get total size of data to transfer'''
        utils.log_msg('Calculating size of data...', level='INFO')

        total_size = 0
        for filename in os.listdir(self._archive_dir):
            total_size = total_size + os.path.getsize(
                os.path.join(self._archive_dir, filename)
            )

        return total_size


    @timer.run_timer
    def do_transfer(self):
        '''
        Transfer all files present in the archive directory for this cycle.
        If requested verify the checksums of all files transferred.
        '''
        if not self._globus_cli:
            remote_host = self._remote_host
        archive_dir = self._archive_dir
        transfer_dir = self._transfer_dir

        # Are there any files to transfer?
        if self._transfer_type == 'push':
            find_cmd = 'ls -A ' + archive_dir
            ret_code, files = utils.exec_subproc(find_cmd, verbose=False)
        else:
            if self._globus_cli:
                msg = 'Using Globus CLI to pull files to JASMIN is not ' + \
                'currently implemented, but could be.'
                utils.log_msg(msg, level='ERROR')
                ret_code = 5
            else:
                find_cmd = 'ssh -oBatchMode=yes ' + remote_host + \
                    ' -n ls -A ' + archive_dir + ' | wc -l'
                ret_code, files = utils.exec_subproc(find_cmd, verbose=False)

        files_found = len(files.split())

        if ret_code == 0:
            if files_found == 0:
                utils.log_msg('-> Nothing to transfer', level='INFO')
                return
        elif ret_code == 255:
            msg = 'Failed: ssh failed whilst checking for files to transfer'
            utils.log_msg(msg, level='FAIL')
            return
        else:
            utils.log_msg('Error checking files to transfer', level='FAIL')
            return

        msg = 'Found {} files in {}'.format(files_found, archive_dir)
        utils.log_msg(msg, level='INFO')

        # Generate checksums for remote files
        if self._verify_chksums:
            if self._generate_checksums():
                msg = 'Checksums generated successfully.'
                utils.log_msg(msg, level='OK')
            else:
                msg = 'Checksum generation failed.'
                utils.log_msg(msg, level='ERROR')
                ret_code = 3

        # Get total size of data to transfer
        bytes = self._get_data_size()
        gigabytes = bytes/1024.0/1024/1024
        utils.log_msg('Total {0:.1f} Gb of data to transfer'.format(gigabytes),
                      level='INFO')

        # Do the transfer.
        # Transfer commands must create the destination directory
        if self._globus_cli:
            # Use globus command-line interface for the file transfer
            utils.log_msg('Transferring files using Globus CLI...',
                          level='INFO')

            verify = '--verify-checksum'
            if self._globus_notify == '':
                notify = ''
            else:
                notify = '--notify {}'.format(self._globus_notify)
            utils.log_msg('notify: {}'.format(notify))
        
            src_coll = self._globus_src_coll
            dst_coll = self._globus_dst_coll
            label =  os.path.join(self._suite_name,
                                  os.environ['CYLC_TASK_CYCLE_POINT'])

            globus_cli_cmd = 'globus transfer --format unix --jmespath ' + \
                '\'task_id\' --recursive --fail-on-quota-errors ' + \
                '--sync-level checksum --label {} {} {}'.\
                format(label, verify, notify)

            if self._transfer_type == 'push':
                transfer_cmd = '{} {}:{} {}:{}'.format(
                    globus_cli_cmd, src_coll, archive_dir,
                    dst_coll, transfer_dir
                    )
                # log the Globus task ID in case we need to inspect it.
                utils.log_msg('Globus CLI command:\n{}'.format(transfer_cmd),
                              level='INFO')
            else:
                msg = 'Using Globus CLI to pull files to JASMIN is not ' + \
                    'currently implemented, but could be.'
                utils.log_msg(msg, level='ERROR')
                ret_code = 5
        else:
            # Use rsync for the file transfer.
            utils.log_msg('Transferring files using rsync', level='INFO')

            if self._transfer_type == 'push':
                remote_host_dir = remote_host + ':' + transfer_dir
                transfer_cmd = 'rsync -av --stats ' \
                               '--rsync-path="mkdir -p {} && rsync" {}/ {}'.\
                               format(transfer_dir,
                                      archive_dir,
                                      remote_host_dir)
            else:
                if not os.path.exists(transfer_dir):
                    msg = 'Creating transfer directory: {}'.format(transfer_dir)
                    utils.log_msg(msg, level='INFO')
                    utils.create_dir(transfer_dir)

                transfer_cmd = 'rsync -av --stats {}:{}/ {}'.format(
                    remote_host, archive_dir, transfer_dir)

        ret_code, output = utils.exec_subproc(transfer_cmd)

        if self._globus_cli:
            # Wait for globus transfer to finish
            utils.log_msg('retcode: {}'.format(ret_code))

            if ret_code == 0:
                globus_task_wait = 'globus task wait -H $task_id'
                task_id = str(output)

                utils.log_msg('Globus task id: {}'.format(task_id), level='OK')
                globus_wait_cmd = 'globus task wait -H {}'.format(task_id)
                ret_code, output = utils.exec_subproc(globus_wait_cmd)

            ret_code = process_globus_retcode(ret_code)

        if ret_code == 0:
            msg = 'Transfer command succeeded: ' + transfer_cmd
            utils.log_msg(msg, level='OK')

            # Perform checksum validation on transferred files - ONLY FOR RSYNC
            if self._verify_chksums:
                if self._globus_cli:
                    msg = 'Cannot use separate verify checksums option ' + \
                        'when using Globus. ' + \
                        'Globus has integral checksumming. ' + \
                        'Set verify_chksums=false to remove this warning.'
                    utils.log_msg(msg, level='WARN')
                else:
                    if self._do_verify_checksums():
                        utils.log_msg('Transfer OK: Checksums verified',
                                      level='OK')
                    else:
                        msg = 'Transfer Failed: Problem with checksum verification'
                        utils.log_msg(msg, level='ERROR')
                        ret_code = 4
        else:
            msg = 'Transfer command failed: ' + transfer_cmd
            utils.log_msg(msg, level='WARN')

        put_rtncode = {
            0:  'Transfer: Transfer OK. (ReturnCode=0)',
            2:  'System Error: Remove archive directory does not exist ' \
                '(ReturnCode=2)',
            3:  'Transfer Error: Checksum generation failed (ReturnCode=3)',
            4:  'Transfer Error: Checksum validation failed (ReturnCode=4)',
            6:  'Globus Error: Network or server error occurred (Globus ReturnCode=1)',
            7:  'Globus Error: Incorrect Command (Globus ReturnCode=2)',
            8:  'Globus Error: Command used on wrong type of object (Globus ReturnCode=3)',
            9:  'Globus Error: Failed authentication or authorization (Globus ReturnCode=4)',
            12: 'System Error: Failed to make transfer directory ' \
                '(ReturnCode=12)',
            }

        if ret_code == 0:
            msg = put_rtncode[0]
            level = 'OK'
        elif ret_code in put_rtncode:
            msg = 'transfer.py: {}'.format(put_rtncode[ret_code])
            level = 'ERROR'
        else:
            msg = 'transfer.py: Unknown Error - Return Code=' + str(ret_code)
            level = 'ERROR'
        utils.log_msg(msg, level=level)

        return ret_code


def process_globus_retcode(rcode):
    '''Translate Globus command return code into one for use by this script'''
    rc_dict = {
            0: 0,
            1: 6,
            2: 7,
            3: 8,
            4: 9,
            }

    if rcode in rc_dict:
        ret_code = rc_dict[rcode]
    else:
        msg = 'transfer.py: Unknown Globus Error - Return Code'.format(rcode)
        utils.log_msg(msg, level='ERROR')

    return ret_code


def main():
    '''Main function'''
    timer.initialise_timer()

    transfer = Transfer()
    ret_code = transfer.do_transfer()

    timer.finalise_timer()

    return ret_code


class PPTransfer(object):
    '''Default namelist for PP Transfer'''
    globus_cli = 'True'
    globus_notify = 'off'
    globus_default_colls = 'True'
    remote_host = ''
    transfer_dir = ''
    transfer_type = 'Push'
    verify_chksums = False


NAMELISTS = {'pptransfer': PPTransfer}


if __name__ == '__main__':
    main()
