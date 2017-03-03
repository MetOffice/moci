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
    control.py

DESCRIPTION
    Base class definition for running models within the post processing app
'''

import abc
import sys
import importlib

import utils


class RunPostProc(object):
    '''
    Control class template for input models
    '''
    __metatclass__ = abc.ABCMeta

    @abc.abstractproperty
    def runpp(self):
        ''' Placeholder for model specific runpp method'''
        msg = 'runpp - Model Post-Processing logical trigger not defined.'
        msg += '\n\t return: boolean'
        utils.log_msg(msg, level='FAIL')
        raise NotImplementedError

    @abc.abstractproperty
    def methods(self):
        ''' Placeholder for model specific methods'''
        msg = 'runpp - Model Post-Processing property not defined.'
        msg += '\n\t return: OrderedDict([ ("MethodName", LogicalValue), ])'
        utils.log_msg(msg, level='FAIL')
        raise NotImplementedError

    @staticmethod
    def _directory(location, title):
        '''
        Returns a titled directory provided via namelist or other means,
        providing the directory exists.
        '''
        location = utils.check_directory(location)
        utils.log_msg('{} directory: {}'.format(title, location))
        return location

    def _debug_mode(self, debug=False):
        '''Model independent setting for global debug_mode variable'''
        utils.set_debugmode(debug)
        self.debug_ok = True

    def finalise_debug(self):
        '''Finalise model with global debug variable'''
        self.debug_ok = utils.get_debugok()


NL = {}

INPUT_MODS = ['suite', 'atmosNamelist', 'nemoNamelist', 'ciceNamelist', 'moo',
              'verify_namelist']

for mod in INPUT_MODS:
    try:
        name = importlib.import_module(mod)
        NL.update(name.NAMELISTS)

    except ImportError:
        if any([(mod == 'suite' and 'main_pp' in sys.argv[0]),
                ('verify' in mod and 'archive integrity' in sys.argv[0])]):
            utils.log_msg('Unable to find suite module', level='FAIL')

    except AttributeError:
        utils.log_msg('Unable to determine default namelists for '
                      '"{}" module'.format(mod), level='WARN')
