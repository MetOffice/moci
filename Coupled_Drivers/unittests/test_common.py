#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_common.py

DESCRIPTION
    Contains unit tests for the common.py module.
'''
import unittest
import os
import random
import glob
import shutil

import common

TEMPDIR = os.getenv('TMPDIR')


class TestSortHistDirs(unittest.TestCase):
    """Unit tests for the _sort_hist_dirs_by_date function."""
    def test_sort_hist_dirs_by_date(self):
        """Check that a date ordered list of directories is returned."""
        dirs = [
            '/path/to/restarts.202101012100',
            '/path/to/restarts.202101012200',
            '/path/to/restarts.202101012300',
            '/path/to/restarts.202101020000'
            ]

        shuffled = dirs.copy()
        random.shuffle(shuffled)

        self.assertEqual(
            common._sort_hist_dirs_by_date(shuffled),
            dirs)

    def test_sort_hist_dirs_bad_date_format(self):
        """Check that an error is thrown if we try to order a list
        of directories that do not have the correct format."""
        dirs = [
            '/path/to/restarts.20210101',
            '/path/to/restarts.20210102',
            '/path/to/restarts.20210103',
            '/path/to/restarts.20210104'
            ]

        shuffled = dirs.copy()
        random.shuffle(dirs)

        with self.assertRaises(SystemExit):
            common._sort_hist_dirs_by_date(shuffled)

    def test_sort_hist_dirs_no_dates(self):
        """Check that an error is thrown if a list of undated, arbitrary
        directories are supplied."""
        dirs = [
            '/path/to/restarts.20210101',
            '/path/to/something/else',
            '/path/to/glu_um_fcst',
            '/path/to/model/output'
            ]

        shuffled = dirs.copy()
        random.shuffle(dirs)

        with self.assertRaises(SystemExit):
            common._sort_hist_dirs_by_date(shuffled)


class TestRemoveDir(unittest.TestCase):
    """Unit test for the remove_latest_hist_dir function."""
    def setUp(self):
        self.dirs = [
            os.path.join(TEMPDIR, 'restarts.202101012100'),
            os.path.join(TEMPDIR, 'restarts.202101012200'),
            os.path.join(TEMPDIR, 'restarts.202101012300'),
            os.path.join(TEMPDIR, 'restarts.202101020000')
            ]

        self.dirpattern = os.path.join(TEMPDIR, 'restarts.*')

        for indir in self.dirs:
            os.mkdir(indir)

    def tearDown(self):
        for indir in glob.glob(self.dirpattern):
            shutil.rmtree(indir)

    def test_remove_latest_hist_dir(self):
        """Check that the most recently dated restart directory is
        deleted."""
        expected_dirs = self.dirs.copy()
        latest_dir = expected_dirs.pop(-1)

        common.remove_latest_hist_dir(latest_dir)

        self.assertCountEqual(
            glob.glob(self.dirpattern),
            expected_dirs
            )
        
class TestPathFunctions(unittest.TestCase):
    '''
    Test the functions relating to dealing with file paths
    '''
    def test_remove_trailing_slash_no_slash(self):
        '''Test that with no trailing slash the path string gets passed
        straight through'''
        path = '/path/with/no/slash'
        self.assertEqual(common.remove_trailing_slash(path), path)

    def test_remove_trailing_slash_with_slash(self):
        '''Test that we successfully strip the trailing slash'''
        path = '/path/with/trailing/slash/'
        self.assertEqual(common.remove_trailing_slash(path), path[:-1])

    def test_remove_three_trailing_slashes(self):
        '''Test that we successfully remove three trailing slashes and
        no initial forward slash'''
        path = 'path/with/three/trailing/slashes///'
        self.assertEqual(common.remove_trailing_slash(path), path[:-3])

    def test_remove_trailing_space(self):
        '''Test that we successfully remove trailing whitespacec'''
        path = '/path/with/trailing/space '
        self.assertEqual(common.remove_trailing_slash(path), path[:-1])

    def test_remove_combo(self):
        '''Test removal of combination of whitespace and slashes'''
        path = '/path/with/trailing/combo/ /\t ///'
        expected_return = '/path/with/trailing/combo'
        self.assertEqual(common.remove_trailing_slash(path), expected_return)

