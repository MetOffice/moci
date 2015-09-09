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
    main_pp.py

SYNOPSIS
    main_pp.py [atmos] [nemocice]

DESCRIPTION
    Post-Processing app for use with Rose Suites - UM vn9.1 ->

ARGUMENTS
    The models to run. Default:
        atmos nemocice
'''

import os
import sys
import importlib

import utils

if len(sys.argv) > 1:
    additional_modules = sys.argv[1:]
else:
    additional_modules = ['atmos', 'nemocice']

for mod in ['common'] + additional_modules:
    sys.path.append(os.path.abspath(os.path.dirname(__file__))+'/'+mod)


def main():
    models = {}

    for name in ['ATMOS', 'NEMO', 'CICE']:
        try:
            mod = importlib.import_module(name.lower())
            models[name] = mod.INSTANCE
        except ImportError:
            # Either the optional import was not requested, or it is not
            # available.
            # A module may not be available if it was not required by the
            # repository extract.
            pass
        except AttributeError:
            utils.log_msg('Unable to find object instance for ' + name, 5)

    for m in models:
        nlfile, mclass = models[m]
        model = mclass(nlfile)
        if model.runpp:
            for meth in model.methods:
                if model.methods[meth]:
                    utils.log_msg('Running {} for {}...'.format(meth, m))
                    getattr(model, meth)()


if __name__ == '__main__':
    main()
