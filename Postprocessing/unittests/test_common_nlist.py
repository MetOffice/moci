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
import os
import sys
import mock

import testing_functions as func
import runtime_environment

# Import of nlist requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import nlist


class NamelistFileTests(unittest.TestCase):
    '''Unit tests relating to namelist files'''
    def setUp(self):
        self.nlfile = 'pp.nl'
        open(self.nlfile, 'w').close()
        self.newnlfile = 'NoFile'
        self.testnl = '''
&testnl
test_variable="Blue",
/
'''
        if not hasattr(sys.stdout, 'getvalue'):
            msg = 'This test requires buffered mode to run (buffer=True)'
            self.fail(msg)

    def tearDown(self):
        for fname in [self.nlfile, self.newnlfile]:
            if os.path.exists(fname):
                os.remove(fname)

    def test_load_one_file(self):
        '''Test load one namelist file'''
        func.logtest('Load single namelist file:')
        with open(self.nlfile, 'w') as handle:
            handle.write(self.testnl)
        namelists = nlist.loadNamelist(self.nlfile)
        self.assertEqual(namelists.testnl.test_variable, 'Blue')

    def test_load_two_files(self):
        '''Test load two namelists - one blank, one non-existent'''
        func.logtest('Load two namelists - one blank, one non-existent:')
        namelists = nlist.loadNamelist(self.nlfile, self.newnlfile)
        self.assertTrue(os.path.exists(self.newnlfile),
                        msg='Failed to create new namelist file: {}'.
                        format(self.newnlfile))
        self.assertEqual(namelists.suitegen.archive_command, 'Moose',
                         msg='Failed to load default &suitegen '
                         '(archive_command=Moose)')

    def test_load_blank_file(self):
        '''Test load one blank file'''
        func.logtest('Load single blank namelist file:')
        namelists = nlist.loadNamelist(self.nlfile)
        attributes = [a for a in dir(namelists) if not a.startswith('__')]
        self.assertListEqual(attributes, [])

    def test_create_unwritable_file(self):
        '''Test attempt to create a file in unwritable location'''
        func.logtest('Attempt to create a file in an unwritable location:')
        with self.assertRaises(SystemExit):
            nlist.create_example_nl('NoDir/' + self.newnlfile)


class ReadNamelistTests(unittest.TestCase):
    '''Unit tests relating to reading namelists'''
    def setUp(self):
        self.nlvars = {
            'integerVar=1': 1,
            'floatVar=1.0': 1.0,
            'arrayVar="a","b",,1,2.5,false,': ['a', 'b', '', 1, 2.5, False],
            'stringVar="$Hello There $$$"': '$Hello There $$$',
            'envVar=$PWD': os.environ['PWD'],
            'execVar=$(echo Hi There!)': 'Hi There!',
            'boolVar=true': True
        }
        if not hasattr(sys.stdout, 'getvalue'):
            msg = 'This test requires buffered mode to run (buffer=True)'
            self.fail(msg)

    def test_read_namlist(self):
        '''Test reading suitegen namelist'''
        func.logtest('Read in namelist with defaults available (suitegen):')
        namelist = nlist.ReadNamelist('suitegen', self.nlvars.keys())
        for line in self.nlvars:
            var, _ = line.split('=')
            self.assertEqual(getattr(namelist, var), self.nlvars[line])
        self.assertEqual(namelist.prefix, os.environ['RUNID'])

    def test_read_no_default_nl(self):
        '''Test reading namelist with no defaults'''
        func.logtest('Attempt to read in namelist with no defaults:')
        nlist.ReadNamelist('noDefault', self.nlvars.keys())
        self.assertIn('[WARN]', func.capture(direct='err'))

    def test_type_casting(self):
        '''Test type casting functionality of _test_val - single values only'''
        func.logtest('Type casting in _test_val (single values only):')
        for line in self.nlvars:
            if isinstance(self.nlvars[line], list):
                continue
            _, val = line.split("=")
            self.assertEqual(type(nlist.ReadNamelist._test_val(val)),
                             type(self.nlvars[line]))

    def test_read_variables_single_line(self):
        '''Test reading a single line array'''
        func.logtest('Read in array length of one:')
        mymock = mock.Mock(nlist.ReadNamelist)
        mymock._uppercase_vars = True
        mymock._test_val = nlist.ReadNamelist._test_val
        nlist.ReadNamelist._read_variables(mymock, 'myColour="blue"')
        self.assertEqual(mymock.MYCOLOUR, 'blue')
