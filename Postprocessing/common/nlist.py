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
    nlist.py

DESCRIPTION
    Container for fortran namelist variables

'''
import os
import re

import control
import utils


class ReadNamelist(object):
    '''Methods required to parse Fortran Namelists'''

    def __init__(self, nl_name, nl_linearray, uppercase_vars=False):
        try:
            # Attempt to set default values for namelist
            baseclass = control.NL[nl_name]
            for attribute in [a for a in dir(baseclass) if
                              not a.startswith('_')]:
                setattr(self, attribute, getattr(baseclass, attribute))
        except KeyError:
            msg = 'readNamelist: No default namelist available: &' + nl_name
            utils.log_msg(msg, level='WARN')

        self._uppercase_vars = uppercase_vars
        self._read_variables(nl_linearray)

    def _read_variables(self, line_array):
        '''
        Read key-value pairs from an input array of lines of a namelist.
        Initialise the key attribute of the ReadNamelist object with the value.
        '''
        if not isinstance(line_array, list):
            line_array = [line_array]

        for line in line_array:
            # Remove whitespace, newlines, and preceding/trailing comma
            try:
                key, val = line.split('=')
                key = key.upper() if self._uppercase_vars else key
                concat_key = False
            except ValueError:
                # Multiline item
                val = line
                concat_key = True

            val = val.strip(',')
            if ',' in val:
                val = map(self._test_val, val.split(','))
            else:
                val = self._test_val(val)

            if concat_key:
                # Concatenate with any existing value(s).
                # Return value MUST be a list.
                previous = getattr(self, key)
                val = (utils.ensure_list(previous) if previous else []) + \
                    (utils.ensure_list(val) if val else [])

            setattr(self, key, val)

    @staticmethod
    def _test_val(valstring):
        ''' Returns appropriate Python variable type '''
        if valstring.lower().strip('\'"') == 'true':
            return True
        elif valstring.lower().strip('\'"') == 'false':
            return False
        elif valstring.lower().strip('\'"') == 'none':
            return None
        elif re.match(r'^\$\(.*\)$', valstring):
            # Attempt to execute implied shell command
            rcode, output = utils.exec_subproc(valstring.strip(r'$()\'"'))
            return output.strip() if rcode == 0 else valstring
        else:
            valstring = valstring.strip('"').strip("'")
            try:
                return int(valstring)
            except ValueError:
                try:
                    return float(valstring)
                except ValueError:
                    # This is a string
                    return os.path.expandvars(valstring).strip()


def loadNamelist(*nl_files):
    '''Load namelist(s) from given file(s)'''
    namelists = utils.Variables()
    for nl_file in nl_files:
        if not os.path.exists(nl_file):
            create_example_nl(nl_file)
        inside_namelist = False
        nl_linelist = []
        try:
            infile = open(nl_file, 'r')
        except IOError:
            msg = 'loadNamelist: Failed to open namelist file for reading: '
            utils.log_msg(msg + nl_file, level='FAIL')

        for line in infile.readlines():
            if line[0] == '&':
                inside_namelist = True
                working_name = line.strip().strip('&')
            elif line[0] == '/':
                inside_namelist = False
                setattr(namelists, working_name,
                        ReadNamelist(working_name, nl_linelist))
                nl_linelist = []
            elif inside_namelist:
                nl_linelist.append(line.strip().strip(','))
        infile.close()

    return namelists


def create_example_nl(nl_file):
    '''
    If no input namelist exist, provide an example using the
    base classes available.
    '''
    nl_text = ''
    for nl_name in control.NL:
        nl_text += '\n&' + nl_name
        for attr in [a for a in dir(control.NL[nl_name])]:
            if attr == 'methods' or attr.startswith('_'):
                continue
            val = getattr(control.NL[nl_name], attr)
            if isinstance(val, tuple):
                if isinstance(val[0], str):
                    val = ['"{}"'.format(v) for v in val]
                val = ','.join([str(x) for x in val])
            elif isinstance(val, bool):
                val = str(val).lower()
            elif isinstance(val, str):
                val = '"' + val + '"'
            nl_text += '\n{}={},'.format(attr, val)
        nl_text += '\n/\n'

    try:
        with open(nl_file, 'w') as outfile:
            outfile.write(nl_text)
    except IOError:
        msg = 'create_example_nl: Failed to open namelist file for writing: '
        utils.log_msg(msg + nl_file, level='FAIL')

    msg = 'Namelist file "{}" does not exist.  The file has been created ' \
        'using default namelists.'.format(nl_file)
    utils.log_msg(msg, level='INFO')
