#!/usr/bin/env python
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    ocn_lib.py

DESCRIPTION
    Library of function required for the ocean models
'''
from collections import namedtuple
import glob
import os
import re
import sys

import common
import error


class ReadOcnNamelist:
    '''
    A class to define the behaviours for reading from a wet model namelist.
    We define the potential variables and their regular expressions to read
    from the namelist file
    '''
    def __init__(self, namelist_file):
        '''
        Constructor for the object to read from given namelist file
        '''
        self._to_read = {}
        self.namelist_file = namelist_file
        NamelistVal = namedtuple('NamelistVal', 'regex value')
        self._variables \
            = {'nemo_first_step': NamelistVal(r'nn_it000=(.+),', None),
               'nemo_last_step': NamelistVal(r'nn_itend=(.+),', None),
               'nemo_step_int': NamelistVal(r'rn_rdt=(\d*)', None),
               'nemo_rst_date': NamelistVal(r'ln_rstdate=(.+),', None),
               'nemo_rst': NamelistVal(
                   r'cn_ocerst_outdir=[\"\'](.*?)[\"\']', None),
               'ice_rst': NamelistVal(
                   r'cn_icerst_outdir=[\"\'](.*?)[\"\']', None),
               'ln_icebergs': NamelistVal(r'ln_icebergs=(.+),', None),
               'top_rst': NamelistVal(
                   r'cn_trcrst_outdir=[\"\'](.*?)[\"\']', None)}

    def read_variables(self, *requested_variables):
        '''
        Read an arbitary number of variable names and return their values.
        If the variable doesnt exist, return none
        '''
        # Reset _to_read
        self._to_read = {}
        for requested_var in requested_variables:
            if requested_var not in self._variables.keys():
                sys.stderr.write('[FAIL] Unable to determine how to read the'
                                 ' variable %s from file %s\n' %
                                 (requested_var, self.namelist_file))
                sys.exit(error.MISSING_FILE_CONTENTS_ERROR)
            self._to_read[requested_var] = self._variables[requested_var]
        self._read_file()
        # loop again to get the output in the correct order
        return_list = []
        for requested_var in requested_variables:
            return_list.append(self._to_read[requested_var].value)
        if len(return_list) == 1:
            return return_list[0]
        return tuple(return_list)

    def _read_file(self):
        '''Read the variables from the namelist file'''
        with open(self.namelist_file, 'r') as nl_fh:
            for line in nl_fh.readlines():
                for var in self._to_read.keys():
                    try:
                        self._to_read[var] \
                            = self._to_read[var]._replace(value=(re.findall(
                                self._to_read[var].regex, line)[0]))
                    except IndexError:
                        pass



#
# Functions to interface to the library
#

def setup_restart(init_dir, restart_link_dir, file_name_label,
                  restart_link_label, nemo_nproc, model_dscr):
    '''
    Setup wet model restart file links (NEMO, TOP, SI3)
    '''
    _create_restart_link_dir(restart_link_dir)
    nproc_str_len = _get_nemo_nproc_str(init_dir)
    if nproc_str_len > 0:
        _setup_multiple_restart(init_dir, restart_link_dir, file_name_label,
                                restart_link_label, nemo_nproc, nproc_str_len)
    else:
        # It is likely we might have a rebuilt restart file
        _setup_single_restart(init_dir, restart_link_dir, file_name_label,
                              restart_link_label, model_dscr)


def setup_nrun(start_envar, restart_link_dir, restart_link_label, init_dir,
               warning_message):
    '''
    Setup restart files for an NRUN
    '''
    _create_restart_link_dir(restart_link_dir)
    if start_envar:
        len_proc_num = _get_nemo_nproc_str(init_dir)
        if os.path.isfile(start_envar):
            restart_link_label = '%s.nc' % restart_link_label
            os.symlink(start_envar,
                       os.path.join(restart_link_dir, restart_link_label))
            ln_restart = ".true."
        elif os.path.isfile('%s_%s.nc' %
                            (start_envar, '0'*len_proc_num)):
            for fname in glob.glob('%s_%s.nc' %
                                   (start_envar, '?'*len_proc_num)):
                proc_number = fname.split('.')[-2][-len_proc_num:]
                restart_link_file = os.path.join(
                    restart_link_dir, '%s_%s.nc' % (restart_link_label,
                                                    proc_number))
                common.remove_file(restart_link_file)
                os.symlink(fname, restart_link_file)
                ln_restart = ".true."
        else:
            sys.stderr.write('[FAIL] file %s not found\n' % (start_envar))
            sys.exit(error.MISSING_MODEL_FILE_ERROR)
    else:
        # Start envar is unset
        sys.stdout.write('[WARN] %s\n' % warning_message)
        ln_restart = ".false."
    return ln_restart

#
# Functions to manipulate restart file links
#

def _get_nemo_nproc_str(restart_file_dir='.'):
    '''
    Get the length of the string in the nemo restart file name containing
    the processor number for unbuilt restart files. For example
    restart_0012.nc would return 4. Takes in a directory to search for
    the restart file. If no directory specified we assume it is in the
    current directory
    '''
    # Find how large the processor tag is on the restart files
    # Get the zero tagged NEMO restart file
    rst_file_glob = '%s/*_[0-9]*_restart_*0.nc' % restart_file_dir
    try:
        zero_nemo_rst = glob.glob(rst_file_glob)[0]
        print(zero_nemo_rst)
        # Get the length of the strings of zeros
        len_proc_num = len(re.search(r'.*_(\d+).nc', zero_nemo_rst).group(1))
    except IndexError:
        len_proc_num = 0
    return len_proc_num


def _setup_multiple_restart(init_dir, restart_link_dir, file_name_label,
                            restart_link_label, nemo_nproc, nproc_str_len):
    '''
    Setup links for multiple (unrebuilt) restart files
    '''
    for i_proc in range(nemo_nproc):
        tag = str(i_proc).zfill(nproc_str_len)
        rst_source = '%s/%s_%s.nc' % (init_dir,
                                      file_name_label,
                                      tag)
        rst_link = os.path.join(restart_link_dir,
                                '%s_%s.nc' % (restart_link_label, tag))
        common.remove_file(rst_link)

        if os.path.isfile(rst_source):
            os.symlink(rst_source, rst_link)

def _setup_single_restart(init_dir, restart_link_dir, file_name_label,
                          restart_link_label, model_dscr):
    '''
    Setup links for single (rebuilt) restart file
    '''
    sys.stdout.write('[INFO] No %s sub-PE restarts found\n' % model_dscr)
    rst_source = '%s/%s.nc' % (init_dir, file_name_label)
    rst_link = os.path.join(restart_link_dir,
                            '%s.nc' % restart_link_label)
    common.remove_file(rst_link)
    if os.path.isfile(rst_source):
        sys.stdout.write('[INFO] Using rebuilt %s restart file %s\n'
                         % (model_dscr, rst_source))
        os.symlink(rst_source, rst_link)

def _create_restart_link_dir(dirname):
    '''
    Try to create the restart link directory, if it already exists we carry
    on as normal'''
    if dirname != '.':
        try:
            os.mkdir(dirname)
        except FileExistsError:
            sys.stdout.write('[INFO] Restart link subdirectory %s exists\n' %
                             dirname)
