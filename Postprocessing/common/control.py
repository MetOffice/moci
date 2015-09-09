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
    control.py

DESCRIPTION
    Base class definition for running models within the post processing app
'''

import abc
import importlib

import utils


class runPostProc(object):
    '''
    Control class template for input models
    '''
    __metatclass__ = abc.ABCMeta

    @abc.abstractproperty
    def runpp(self):
        msg = 'runpp - Model Post-Processing logical trigger not defined.'
        msg += '\n\t return: boolean'
        utils.log_msg(msg, 4)
        raise NotImplementedError

    @abc.abstractproperty
    def methods(self):
        msg = 'runpp - Model Post-Processing property not defined.'
        msg += '\n\t return: OrderedDict([ ("MethodName", LogicalValue), ])'
        utils.log_msg(msg, 4)
        raise NotImplementedError

NL = {}

input_modules = ['suite', 'atmosNamelist', 'nemoNamelist', 'ciceNamelist']

for mod in input_modules:
    try:
        name = importlib.import_module(mod)
        NL.update(name.NAMELISTS)

    except ImportError:
        if mod == 'suite':
            utils.log_msg('Unable to find suite module', 5)

    except AttributeError:
        utils.log_msg('Unable to determine default namelists for ' + mod, 3)
