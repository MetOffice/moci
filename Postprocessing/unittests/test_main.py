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
'''
import unittest
import mock
import os
import sys
from collections import OrderedDict

import runtimeEnvironment
import testing_functions as func
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'atmos'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'nemocice'))
import main_pp

class PostprocTests(unittest.TestCase):
    '''Unit tests relating to main postprocessing control'''
    def setUp(self):
        self.methods = OrderedDict([('method1', True),
                                    ('method2', False)])

    def tearDown(self):
        for fname in ['atmospp.nl', 'nemocicepp.nl']:        
            try:
                os.remove(fname)
            except OSError:
                pass
        # Tidy up imported modules to prevent interference between tests
        for mod in ['atmos', 'nemo', 'cice']:
            try:
                del sys.modules[mod]
            except KeyError:
                pass

    def test_import_failure(self):
        '''Test failure mode attempting to import a module'''
        func.logtest('Assert failure to import a module:')
        sys.argv = ('script', 'atmos')
        with mock.patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError
            with self.assertRaises(SystemExit):
                main_pp.main()
            mock_import.assert_called_with('atmos')
        self.assertIn('Error during import of model ATMOS',
                      func.capture('err'))

    def test_atmos_instantiation(self):
        '''Test instantiation of atmos model only'''
        func.logtest('Assert successful instantiation of atmos model:')
        sys.argv = ('script', 'atmos')
        with mock.patch('control.runPostProc') as mock_atmos:
            mock_atmos.runpp = True
            mock_atmos.methods = self.methods
            main_pp.main()
        self.assertIn('Running method1 for atmos', func.capture())
        self.assertNotIn('Running method2 for atmos', func.capture())
        self.assertNotIn('Running method1 for nemo', func.capture())
        self.assertNotIn('Running method1 for cice', func.capture())

    def test_nemo_instantiation(self):
        '''Test instantiation of nemo model only'''
        func.logtest('Assert successful instantiation of nemo model:')
        sys.argv = ('script', 'nemo')
        with mock.patch('modeltemplate.ModelTemplate') as mock_nemo:
            mock_nemo.runpp = True
            mock_nemo.methods = self.methods
            main_pp.main()
        self.assertIn('Running method1 for nemo', func.capture())
        self.assertNotIn('Running method1 for atmos', func.capture())
        self.assertNotIn('Running method1 for cice', func.capture())

    def test_cice_instantiation(self):
        '''Test instantiation of cice model only'''
        func.logtest('Assert successful instantiation of cice model:')
        sys.argv = ('script', 'cice')
        with mock.patch('modeltemplate.ModelTemplate') as mock_nemo:
            mock_nemo.runpp = True
            mock_nemo.methods = self.methods
            main_pp.main()
        self.assertIn('Running method1 for cice', func.capture())
        self.assertNotIn('Running method1 for atmos', func.capture())
        self.assertNotIn('Running method1 for nemo', func.capture())

    def test_nemocice_instantiation(self):
        '''Test instantiation of nemocice models only'''
        func.logtest('Assert successful instantiation of nemocice model:')
        sys.argv = ('script', 'cice', 'nemo')
        with mock.patch('modeltemplate.ModelTemplate') as mock_nc:
            print 'mock_nc=', mock_nc
            mock_nc.runpp = True
            mock_nc.methods = self.methods
            main_pp.main()
        self.assertIn('Running method1 for cice', func.capture())
        self.assertIn('Running method1 for nemo', func.capture())
        self.assertNotIn('Running method1 for atmos', func.capture())

    def test_all_models(self):
        '''Test instantiation of all models'''
        func.logtest('Assert successful instantiation of all models:')
        sys.argv = ('script',)
        main_pp.main()
        self.assertTrue(os.path.exists('atmospp.nl'))
        self.assertTrue(os.path.exists('nemocicepp.nl'))

    def test_dummy_model(self):
        '''Test instantiation of a non-existent dummy model'''
        func.logtest('Assert failed attempt to instantiate dummy model:')
        sys.argv = ('script', 'atmos', 'dummy', 'nemo')
        with self.assertRaises(SystemExit):
            main_pp.main()
        self.assertIn('Unknown model(s) requested: dummy',
                      func.capture('err'))

    def test_atmos_failure(self):
        '''Test runtime failure of atmos model'''
        func.logtest('Assert runtime failure of atmos model:')
        sys.argv = ('script',)
        with mock.patch('control.runPostProc') as mock_atmos:
            mock_atmos.runpp = True
            mock_atmos.suite.archiveOK = False
            with mock.patch('modeltemplate.ModelTemplate') as mock_nemo:
                mock_nemo.runpp = True
                mock_nemo.suite.archiveOK = True
                with self.assertRaises(SystemExit):
                    main_pp.main()
        self.assertIn('Exiting with errors in atmos', func.capture('err'))
        self.assertNotIn('nemo', func.capture('err'))
        self.assertNotIn('cice', func.capture('err'))

    def test_nemocice_failure(self):
        '''Test runtime failure of atmos model'''
        func.logtest('Assert runtime failure of atmos model:')
        sys.argv = ('script',)
        with mock.patch('control.runPostProc') as mock_atmos:
            mock_atmos.runpp = True
            mock_atmos.suite.archiveOK = True
            with mock.patch('modeltemplate.ModelTemplate') as mock_nemo:
                mock_nemo.runpp = True
                mock_nemo.suite.archiveOK = False
                with self.assertRaises(SystemExit):
                    main_pp.main()
        self.assertIn('Exiting with errors in', func.capture('err'))
        self.assertIn('nemo', func.capture('err'))
        self.assertIn('cice', func.capture('err'))
        self.assertNotIn('atmos', func.capture('err'))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
