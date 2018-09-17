#!/usr/bin/env python
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
#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
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
        the keys of which are the names for the model components and the
        values are the method to run the update process for that particular
        component model
        '''

        self.models_to_update = {'mct': self.add_mct_details,
	                         'um': self.add_um_details,
				 'nemo': self.add_nemo_details,}

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
        Update namcouple details specifcally relevant to the UM.
        '''
	# Nothing to do currently
        pass

    def add_nemo_details(self):
        '''
        Update namcouple details specifically relevant to NEMO.
        '''
        # Nothing to do currently
        pass

    def add_mct_details(self):
        '''
        Update general namcouple details required by OASIS3-MCT.
        '''
	
	# The coupler needs to know the run length of this cycle. 
        seconds = common.setup_runtime()
	
        #Edit the namcouple file
        namc_file_in, namc_file_out = _start_edit_namcouple()
        edit_runtime = False
        ignore_line = False

        for line in namc_file_in.readlines():
            # Look for the run time header $RUNTIME. 
	    # The namcouple format rules prescribe that each section header should
	    # startwith the presence of a $ in column 2 thus: " $"
	    # Thus, triggers are based on testing for this at the start
	    # of the line.   
            if re.match(r'^ \$RUNTIME', line ):
                edit_runtime = True
                namc_file_out.write(line)
            elif edit_runtime:
                # Once we've found the line we need to write the run length
                # on we write it and close the $RUNTIME header section
                # and ignore all further lines until we find a line
                # featuring " $" at the start, at which point we start 
		# writing out lines again to our target file.
                namc_file_out.write('# Runtime setting automated via suite'
                                    ' run length settings\n')
                namc_file_out.write('  %i\n' % seconds)

                edit_runtime = False
                ignore_line = True
            elif ignore_line:
                # Look for the next keyword which will start with " $".
                # As for the header this is always indented by a single space
                # in the namcouple file
                if re.match(r'^ \$', line ):
                    ignore_line = False
                    namc_file_out.write(line)
            else:
                namc_file_out.write(line)

        _end_edit_namcouple(namc_file_in, namc_file_out)
	
def _start_edit_namcouple(fname='namcouple'):
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
