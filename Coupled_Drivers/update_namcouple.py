#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    update_namcouple.py

DESCRIPTION
    Top level module to provide any dynamic adjustment of the namcouple
    file required for coupled models.

    Note that OASIS3-MCT is fussy about the section headers starting in
    column 2 with a "$" sign. Any other positioning will lead to errors.
'''
import sys
import re
import os
import error
import common

class _UpdateComponents(object):
    '''
    Update the namcouple file relating to the components to be coupled
    with MCT
    '''

    def __init__(self):
        '''
        Initialise the class. Member models_to_update contains a dictionary,
        the keys of which are the names for the component models, and the
        values are the method to run the update process for that particular
        model
        '''

        self.models_to_update = {'nemo': self.add_nemo_details,
                                 'um': self.add_um_details}

    def update(self, models):
        '''
        Run the update process. Takes a space separated string of models that
        are coupled in this particular configuration
        '''
        for model in models.split():
            try:
                self.models_to_update[model]()
            except KeyError:
                sys.stdout.write('[FAIL] update_namcouple can not update the'
                                 ' %s component' % model)
                sys.exit(error.INVALID_DRIVER_ARG_ERROR)

    def add_um_details(self):
        '''
        Add details required for running the UM component
        '''
        pass

    def add_nemo_details(self):
        '''
        Add details required for running the NEMO component
        '''
        nemo_namcouple_envar = common.LoadEnvar()
        nemo_namcouple_envar.load_envar('NEMO_NL', 'namelist_cfg')
        nemo_nl = nemo_namcouple_envar['NEMO_NL']
        #get nemo start timestep
        _, first_step_val = common.exec_subproc(['grep', 'nn_it000=',
                                                 nemo_nl])
        nemo_first_step = int(re.findall(r'.+=(.+),', first_step_val)[0])

        #get nemo end timestep
        _, last_step_val = common.exec_subproc(['grep', 'nn_itend=',
                                                nemo_nl])
        nemo_last_step = re.findall(r'.+=(.+),', last_step_val)[0]
        if 'set_by_system' in nemo_last_step:
            nemo_last_step = 0
        else:
            nemo_last_step = int(nemo_last_step)

        #integer number of seconds per timestep
        _, nemo_step_int_val = common.exec_subproc(['grep', 'rn_rdt=',
                                                    nemo_nl])
        nemo_step_int = int(re.findall(r'.+=(\d*)', nemo_step_int_val)[0])

        # Calculate the total number of timesteps for the run. In this version
        # we do not add 1 day to allow N+1 coupling exchanges in N days. This
        # caters for the rearranged model timestepping where there is no final
        # exchange prior to dump creation.
        seconds = (nemo_last_step - nemo_first_step + 1) * nemo_step_int

        #Edit the namcouple file
        namc_file_in, namc_file_out = _start_edit_namecouple()
        edit_runtime = False
        ignore_line = False

        for line in namc_file_in.readlines():
            # Look for the run time header section starting in the 2nd
            # column.
            if r'^ \$RUNTIME' in line:
                edit_runtime = True
                namc_file_out.write(line)
            elif edit_runtime:
                # Once we've found the line we need to write the run length
                # on we write it and close the $RUNTIME header section
                # and ignore all further lines until we find a line
                # featuring $END at which point we start writing out
                # lines again to our target file.
                namc_file_out.write('# Runtime setting automated via NEMO'
                                    ' namelist values\n')
                namc_file_out.write('  %i\n' % seconds)
                namc_file_out.write(' $END\n')
                edit_runtime = False
                ignore_line = True
            elif ignore_line:
                if r'^ \$END' in line:
                    ignore_line = False
            else:
                namc_file_out.write(line)

        _end_edit_namcouple(namc_file_in, namc_file_out)

def _start_edit_namecouple(fname='namcouple'):
    '''
    Open the original namcouple file for input and a new file for output.
    Returns two file handles, the first for the exisiting file to be read,
    and the second for a temporary file to be written.
    '''
    namc_file_in = common.open_text_file(fname, 'r')
    namc_file_out = common.open_text_file('%s.out' % fname, 'w')
    return namc_file_in, namc_file_out

def _end_edit_namcouple(namc_file_in, namc_file_out):
    '''
    Close the two namcouple pairs, takes the input and output filehandles as
    an argument, then overwrite old with the new
    '''
    namc_file_in.close()
    namc_file_out.close()
    os.rename(namc_file_out.name, namc_file_in.name)

def update(models):
    '''
    Update the Namcouple file. Takes a list containing the models coupled via
    MCT
    '''

    # Componentwise update of namcouple
    components = _UpdateComponents()
    components.update(models)
