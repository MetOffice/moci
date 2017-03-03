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
    main_pp.py

SYNOPSIS
    main_pp.py [atmos] [nemo] [cice]

DESCRIPTION
    Post-Processing app for use with Rose Suites - UM vn9.1 ->

ARGUMENTS
    The models to run.
        Default: atmos nemo cice
'''

import os
import sys
import importlib

import timer
import utils
try:
    import archive_integrity
except ImportError:
    pass
    
def run_postproc():
    '''Main function for PostProcessing App'''
    timer.initialise_timer()
    # models dictionary:
    #    Key = Name of top-level module for model - used as argument to
    #          main_pp.py
    #    Value = Directory relative to main_pp.py containing the above module
    models = {
        'atmos': 'atmos',
        'nemo': 'nemocice',
        'cice': 'nemocice',
        }

    if len(sys.argv) > 1:
        models = {k: v for k, v in models.items() if k in sys.argv[1:]}
        unknown = [a for a in sys.argv[1:] if a not in models]
        if any(unknown):
            msg = 'main_pp.py - Unknown model(s) requested: '
            utils.log_msg(msg + ','.join(unknown), level='FAIL')

        for mod in ['common'] + [v for v in models.values()]:
            sys.path.append(os.path.join(os.path.dirname(__file__),
                                         os.pardir, mod))

    for name in models:
        try:
            impmod = importlib.import_module(name)
            models[name] = impmod.INSTANCE
        except ImportError as err:
            msg = 'main_pp.py - Error during import of model {}\n\t {}'.\
                format(name.upper(), err)
            utils.log_msg(msg, level='FAIL')

    exit_check = {}
    for name in models:
        nlfile, mclass = models[name]
        model = mclass(nlfile)
        if model.runpp:
            for meth in model.methods:
                if model.methods[meth]:
                    utils.log_msg('Running {} for {}...'.format(meth, name))
                    getattr(model, meth)()
            exit_check[name + '_archive'] = model.suite.archive_ok
            exit_check[name + '_debug'] = model.debug_ok

    timer.finalise_timer()
    if not all(exit_check.values()):
        fails = [m for m, v in exit_check.items() if not v]
        msg = 'main_pp.py - PostProc complete. Exiting with errors in '
        utils.log_msg(msg + ', '.join(fails), level='FAIL')


def run_archive_integrity():
    '''Main function for Archive Verification App'''
    try:
        # For rose stem (testing) purposes - process archive log
        testing_log = os.environ['PP_TESTING_LOG']
        utils.exec_subproc(testing_log, verbose=False)
    except KeyError:
        pass

    try:
        run_verify = os.environ['VERIFY_ARCHIVE'].lower() == 'true'
    except KeyError:
        run_verify = False

    if run_verify:
        utils.log_msg('', level='INFO')
        utils.log_msg(' *** Running archive integrity verification app ***',
                      level='INFO')
        utils.log_msg('', level='INFO')
        archive_integrity.main()


def main():
    '''Main function'''
    # Run main post processing app
    run_postproc()

    # Run verification app as required
    run_archive_integrity()


if __name__ == '__main__':
    main()
