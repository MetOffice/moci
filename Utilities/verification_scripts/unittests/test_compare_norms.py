#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2020 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************

NAME
    test_compare_norms.py

DESCRIPTION
    Unit tests for compare_absnorms.py
'''
import os
import sys
from copy import deepcopy
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(HERE, os.pardir))
import compare_absnorms


class TimestepTests(unittest.TestCase):
    ''' Unit tests for Timestep object '''
    def setUp(self):
        self.tstep = compare_absnorms.Timestep('ABCD')

    def tearDown(self):
        pass

    def test_instantiation(self):
        ''' Assert instantiation of Timestep object '''
        self.assertIsInstance(self.tstep, compare_absnorms.Timestep)
        self.assertEqual(self.tstep.timestamp, 'ABCD')
        self.assertIsNone(self.tstep.initial_norm)
        self.assertIsNone(self.tstep.final_norm)
        self.assertIsNone(self.tstep.iterations)

    def test_add_initial_norm(self):
        ''' Assert successful addition of an initial norm '''
        self.tstep.add_norm('4', '1.234e05')
        self.assertEqual(self.tstep.initial_norm, 1.234e5)
        self.assertEqual(self.tstep.iterations, 4)
        self.assertIsNone(self.tstep.final_norm)

    def test_add_final_norm(self):
        ''' Assert succesful addition of a final norm '''
        self.tstep.add_norm('4', '1.234e05')
        self.tstep.add_norm('3', '5.432e01')
        self.assertEqual(self.tstep.initial_norm, 1.234e5)
        self.assertEqual(self.tstep.final_norm, 54.32)
        self.assertEqual(self.tstep.iterations, 3)

    def test_get_timestamp(self):
        ''' Assert retrieval of the timestamp attribute value '''
        self.assertEqual(self.tstep.get_value('timestamp'), 'ABCD')

    def test_get_bad_attribute(self):
        ''' Assert failure to get value of non-existent attribute '''
        with self.assertRaises(AttributeError):
            self.tstep.get_value('MyAttribute')


class TestCompareFiles(unittest.TestCase):
    ''' Unit tests for Timestep object '''
    def setUp(self):
        self.kgofile = os.path.join(HERE, 'norms_kgo')
        self.emptyfile = os.path.join(HERE, 'norms_emptyfile')
        self.kgo = {}
        for i in range(10):
            name = 'TS' +str(i)
            self.kgo[name] = compare_absnorms.Timestep(name)
            self.kgo[name].add_norm(i, 10^i)
            self.kgo[name].add_norm(i+1, 10^i-1)

    def tearDown(self):
        pass

    def test_generate_timestep(self):
        ''' Assert yield variable type from the timestep generator '''
        tsteps = list(compare_absnorms.generate_timestep(self.kgofile))
        self.assertIsInstance(tsteps[0], compare_absnorms.Timestep)

    def test_generate_no_norms(self):
        ''' Assert yield from a file containing no norms data '''
        tsteps = list(compare_absnorms.generate_timestep(self.emptyfile))
        self.assertListEqual(tsteps, [])

    def test_generate_no_file(self):
        ''' Assert SystemExit from the generator due to non-existent file '''
        with self.assertRaises(SystemExit):
            _ = list(compare_absnorms.generate_timestep('NotAFile'))

    def test_create_timesteps(self):
        ''' Assert creation of a timesteps dictionary '''
        tsteps = compare_absnorms.create_timesteps(self.kgofile)
        self.assertIsInstance(tsteps, dict)
        self.assertIsInstance(tsteps[tsteps.keys()[0]],
                              compare_absnorms.Timestep)

    def test_compare_timesteps(self):
        ''' Assert successful comparison of norms '''
        rcode, msg = compare_absnorms.compare_timesteps(self.kgo, self.kgo)
        self.assertEqual(0, rcode)
        self.assertIn('10 timesteps checked and norms are OK', msg)

    def test_compare_different_ts(self):
        ''' Assert no matching timesteps available in kgo and comparator '''
        testpe = {}
        for tstep in self.kgo:
            testpe[tstep + 'B'] = self.kgo[tstep]

        rcode, msg = compare_absnorms.compare_timesteps(self.kgo, testpe)
        self.assertEqual(-1, rcode)
        self.assertIn('No matching timesteps', msg)

    def test_compare_ts_not_in_kgo(self):
        ''' Assert additional timesteps in the comparison file '''
        testpe = {}
        for tstep in self.kgo:
            if int(tstep[-1]) % 2 == 0:
                testpe[tstep] = self.kgo[tstep]

        rcode, msg = compare_absnorms.compare_timesteps(testpe, self.kgo)
        self.assertEqual(-1, rcode)
        self.assertIn('5 timestep norms not found in KGO file', msg)

    def test_compare_differences(self):
        ''' Assert differences in norms '''
        testpe = deepcopy(self.kgo)
        testpe['TS3'].initial_norm = 5000
        testpe['TS5'].final_norm = 10
        testpe['TS7'].iterations = 0

        rcode, msg = compare_absnorms.compare_timesteps(self.kgo, testpe)
        self.assertEqual(-1, rcode)
        self.assertIn('3 differences', msg)
        for tstep in ['TS3', 'TS5', 'TS7']:
            self.assertIn(tstep, msg)

    def test_compare_empty(self):
        ''' Assert an empty file as kgo or comparator '''
        rcode, msg = compare_absnorms.compare_timesteps(self.kgo, {})
        self.assertEqual(-1, rcode)
        self.assertIn('Norms data not found', msg)


if __name__ == '__main__':
    unittest.main()
