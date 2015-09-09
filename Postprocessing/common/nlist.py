#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
(C) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
*****************************COPYRIGHT******************************
--------------------------------------------------------------------
 Code Owner: Please refer to the UM file CodeOwners.txt
 This file belongs in section: Rose scripts
--------------------------------------------------------------------
NAME
    nlist.py

DESCRIPTION
    Container for fortran namelist variables

'''
import os

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
        except AttributeError:
            pass
        except KeyError:
            log = 'No default namelist available: &' + nl_name
            utils.log_msg(log, 3)

        self.__uppercase_vars = uppercase_vars
        self.__readVariables(nl_linearray)

    def __readVariables(self, line_array):
        for line in line_array:
            # Remove whitespace, newlines, and trailing comma
            key, val = line.split('=')
            if ',' in val:
                val = map(self.__testVal, val.split(','))
            else:
                val = self.__testVal(val)

            key = key.upper() if self.__uppercase_vars else key
            setattr(self, key, val)

    def __testVal(self, valstring):
        ''' Returns appropriate Python variable type '''
        if 'true' in valstring.lower():
            return True
        elif 'false' in valstring.lower():
            return False
        else:
            valstring = valstring.strip('"').strip("'")
            try:
                return int(valstring)
            except ValueError:
                try:
                    return float(valstring)
                except ValueError:
                    # This is a string
                    return os.path.expandvars(valstring)


def loadNamelist(*nl_files):
    namelists = utils.Variables()
    for nl_file in nl_files:
        if not os.path.exists(nl_file):
            create_example_nl(nl_file)
        inside_namelist = False
        nl_linelist = []
        try:
            infile = open(nl_file, 'r').readlines()
        except IOError:
            msg = 'Failed to open namelist file for reading: ' + nl_file
            utils.log_msg(msg, 5)

        for line in infile:
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

    return namelists


def create_example_nl(nl_file):
    '''
    If no input namelist exist, provide an example using the
    base classes available.
    '''
    # Input file does not exist. Write out namelist example and exit
    nl_text = ''
    for nl_name in control.NL:
        nl_text += '\n&' + nl_name
        for attr in [a for a in dir(control.NL[nl_name])]:
            if attr == 'methods' or attr.startswith('_'):
                continue
            val = getattr(control.NL[nl_name], attr)
            if type(val) == tuple:
                if type(val[0]) == str:
                    val = map(lambda v: '"' + v + '"', val)
                val = ','.join([str(x) for x in val])
            elif type(val) == bool:
                val = str(val).lower()
            elif type(val) == str:
                val = '"' + val + '"'
            nl_text += '\n{}={},'.format(attr, val)
        nl_text += '\n/\n'

    try:
        open(nl_file, 'w').write(nl_text)
    except IOError:
        msg = 'Failed to open namelist file for writing: ' + nl_file
        utils.log_msg(msg, 5)
    close(nl_file)

    msg = 'Namelist file {} does not exist.  An example has been created.'.\
        format(nl_file)
    utils.log_msg(msg, 2)
