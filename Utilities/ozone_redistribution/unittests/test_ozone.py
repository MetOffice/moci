#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import sys
import os
import shutil
import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import retrieve_ozone_data

class OzoneDataProcessingTests(unittest.TestCase):
    ''' Unit tests for methods processing ozone data retrieval request '''
    def setUp(self):
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19950101T0000Z'
        os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT'] = '19900901T0000Z'
        os.environ['DATAM'] = 'History_Data'
        os.environ['OZONE_SHARE'] = 'ozone_share'
        os.environ['RUNID'] = 'RUNID'
        os.environ['SOURCE_STREAM'] = 'p4'
        os.environ['CYLC_SUITE_NAME'] = 'u-aa000'
        os.environ['UMTASK'] = 'coupled'
        os.environ['OZONE_ANCIL'] = 'ancil1995file'
        retrieve_ozone_data.setup_environment()
        self.env = retrieve_ozone_data.ENV


    def tearDown(self):
        pass

    def test_environment(self):
        '''Test environment_setup'''

        self.assertEqual(self.env.SOURCE_STREAM, 'p4')
        self.assertEqual(self.env.GET_STASH, '253, 30453')

    def test_environment_missing(self):
        '''Test environment_setup with missing variable'''
        del os.environ['DATAM']
        with self.assertRaises(retrieve_ozone_data.
                               OzoneEnvironmentError) as exc:
            retrieve_ozone_data.setup_environment()
        self.assertTrue('Required variable DATAM is not available'
                        in str(exc.exception))

    def test_task_info(self):
        '''Test the task information printed to stdout'''
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.task_info()
        for line in [r'files matching "RUNIDa.p4[1993|1994]*.pp"',
                     'Initial cycle point: 19900901T0000Z',
                     'Current cycle point: 19950101T0000Z',
                     r'\t\t1993=Yes, 1994=Yes']:
            self.assertTrue(any(line in str(c)
                                for c in mock_out.write.mock_calls))
        self.assertFalse(any('archive_source' in str(c)
                             for c in mock_out.write.mock_calls))

    def test_task_info_archive_sources(self):
        '''Test the task information printed to stdout with archive sources'''
        self.env.add_var('CYLC_SUITE_INITIAL_CYCLE_POINT',
                         varval='19940601T0000Z')
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.task_info()

        for line in [r'\t\t1993=No, 1994=Partial',
                     'Primary archive source:',
                     'Secondary archive source:']:
            self.assertTrue(any(line in str(c)
                                for c in mock_out.write.mock_calls))

    def test_cyclepoint(self):
        '''Test parsing of Cylc cyclepoint string'''
        task_cycle = retrieve_ozone_data.cyclepoint(
            self.env.CYLC_TASK_CYCLE_POINT
        )
        self.assertListEqual(task_cycle, [1995, 1, 1])

    def test_cyclepoint_fail(self):
        '''Test parsing of Cylc cyclepoint string'''
        with self.assertRaises(retrieve_ozone_data.
                               OzoneEnvironmentError) as exc:
            _ = retrieve_ozone_data.cyclepoint('CyclePoint')
        self.assertTrue('Cannot parse the cycle point: CyclePoint'
                        in str(exc.exception))

    def test_stash_fmt(self):
        '''Test parsing of STASHcode'''
        stash = retrieve_ozone_data.stash_fmt('12345')
        self.assertEqual(stash, 'm01s12i345')
        stash = retrieve_ozone_data.stash_fmt(91)
        self.assertEqual(stash, 'm01s00i091')
        stash = retrieve_ozone_data.stash_fmt(None)
        self.assertEqual(stash, 'm01s0Nione')

    @mock.patch('retrieve_ozone_data.os')
    def test_link_sourcefiles(self, mock_os):
        '''Test soft links to sourcefiles'''
        mock_os.path.exists.return_value = True
        mock_os.path.join = os.path.join
        mock_os.listdir.side_effect = [['file1', 'file2']]
        mock_os.symlink.side_effect = [None,
                                       retrieve_ozone_data.SymlinkExistsError,
                                       None]

        with mock.patch('retrieve_ozone_data.re.match', return_value=True):
            rval = retrieve_ozone_data.link_sourcefiles(1998, False)

        self.assertTrue(rval)
        self.assertListEqual(mock_os.listdir.mock_calls,
                             [mock.call('ozone_share/model_data')])
        self.assertIn(mock.call.symlink('ozone_share/model_data/file1',
                                        'ozone_share/file1'),
                      mock_os.mock_calls)
        self.assertIn(mock.call.symlink('ozone_share/model_data/file2',
                                        'ozone_share/file2'),
                      mock_os.mock_calls)

        self.assertNotIn(mock.call.unlink('ozone_share/file1'),
                         mock_os.mock_calls)
        self.assertIn(mock.call.unlink('ozone_share/file2'),
                      mock_os.mock_calls)

    @mock.patch('retrieve_ozone_data.os')
    def test_link_sourcefiles_no_datam(self, mock_os):
        '''Test soft links to sourcefiles - unable to access $DATAM'''
        mock_os.path.exists.return_value = False
        mock_os.path.join = os.path.join
        mock_os.listdir.side_effect = [['file1', 'file2']]
        mock_os.symlink.side_effect = [None,
                                       retrieve_ozone_data.SymlinkExistsError,
                                       None]

        with self.assertRaises(retrieve_ozone_data.
                               OzoneSourceNotFoundError) as exc:
            _ = retrieve_ozone_data.link_sourcefiles(1998, False)
        self.assertTrue('Unable to access link to model data'
                        in str(exc.exception))

    @mock.patch('retrieve_ozone_data.os')
    def test_link_sourcefiles_first_cycle(self, mock_os):
        '''Test soft links to sourcefiles - first cycle'''
        mock_os.path.exists.return_value = False

        rval = retrieve_ozone_data.link_sourcefiles(1998, True)
        self.assertFalse(rval)
        self.assertListEqual(mock_os.listdir.mock_calls, [])

    def test_get_archived_data(self):
        '''Test call to archive retrieval script'''
        self.env.add_var('RETRIEVE_ARCHIVE_SCRIPT', 'myscript')
        yr_data = mock.Mock()
        yr_data.complete_year = False
        yr_data.year = 2002
        yr_data.missing_months = [7, 8, 9, 10]
        with mock.patch('retrieve_ozone_data.os.path.isfile',
                        return_value=True):
            with mock.patch('retrieve_ozone_data.shell_cmd',
                            return_value=0) as mock_exec:
                rtn_data = retrieve_ozone_data.get_archived_data(
                    yr_data, 'myarchivepath', 5)
        mock_exec.assert_called_once_with(
            'myscript -a myarchivepath -y 2002 -f 7 -l 10 '
            '-s 253,30453 -o RUNIDa.p42002_arch5.pp'
            )
        yr_data.load_data.assert_called_once_with()
        self.assertEqual(rtn_data, yr_data)

    def test_get_archived_data_fail(self):
        '''Test failed call to archive retrieval script'''
        self.env.add_var('RETRIEVE_ARCHIVE_SCRIPT', 'myscript')
        yr_data = mock.Mock()
        yr_data.complete_year = False
        yr_data.year = 2002
        yr_data.missing_months = [7, 8, 9, 10]
        with mock.patch('retrieve_ozone_data.os.path.isfile',
                        return_value=True):
            with mock.patch('retrieve_ozone_data.shell_cmd',
                            return_value=-1) as mock_exec:
                with self.assertRaises(retrieve_ozone_data.
                                       OzoneArchiveRetrievalError) as exc:
                    _ = retrieve_ozone_data.get_archived_data(
                        yr_data, 'myarchivepath', 5
                    )
        self.assertTrue('Failed in archive retrieval script: myscript'
                        in str(exc.exception))
        mock_exec.assert_called_once_with(
            'myscript -a myarchivepath -y 2002 -f 7 -l 10 '
            '-s 253,30453 -o RUNIDa.p42002_arch5.pp'
            )

    def test_get_archived_data_complete(self):
        '''Test no calls to archive retrieval script - complete datad'''
        yr_data = mock.Mock()
        yr_data.complete_month = True
        rtn_data = retrieve_ozone_data.get_archived_data(yr_data,
                                                         'myarchivepath',
                                                         5)
        self.assertEqual(yr_data, rtn_data)

    def test_get_archived_data_no_script(self):
        '''Test calls to missing archive retrieval script'''
        self.env.add_var('RETRIEVE_ARCHIVE_SCRIPT', 'myscript')
        yr_data = mock.Mock()
        yr_data.complete_year = False

        with self.assertRaises(retrieve_ozone_data.
                               OzoneArchiveRetrievalError) as exc:
            _ = retrieve_ozone_data.get_archived_data(
                yr_data, 'myarchivepath', 5
            )
        self.assertTrue('archive retrieval script does not exist: myscript'
                        in str(exc.exception))

    def test_get_archived_data_no_path(self):
        '''Test get_archived_data with no archive path'''
        yr_data = mock.Mock()
        yr_data.complete_month = False

        rtn_data = retrieve_ozone_data.get_archived_data(yr_data, None, 5)
        self.assertEqual(yr_data, rtn_data)

    def test_skip_redistribution(self):
        '''Test call to `cylc brodcast` to skip redistribution'''
        with mock.patch('retrieve_ozone_data.shell_cmd') as mock_exec:
            retrieve_ozone_data.skip_redistribution()

        expected_cmds = [
            # Nullify further ozone tasks this cycle
            'cylc broadcast u-aa000 -n redistribute_ozone -p 19950101T0000Z '
            '-s script="echo [INFO] No redistribution required in the '
            'first year of simulation" -s post-script=""',
            'cylc broadcast u-aa000 -n rose_arch_ozone -p 19950101T0000Z '
            '-s script="echo [INFO] No redistribution required in the '
            'first year of simulation" -s post-script=""',
            # Update ozone ancillary for remaining UM tasks this year
            'cylc broadcast u-aa000 -n coupled '
            '-p 19950101T0000Z -p 19950111T0000Z -p 19950121T0000Z '
            '-p 19950201T0000Z -p 19950211T0000Z -p 19950221T0000Z '
            '-p 19950301T0000Z -p 19950311T0000Z -p 19950321T0000Z '
            '-p 19950401T0000Z -p 19950411T0000Z -p 19950421T0000Z '
            '-p 19950501T0000Z -p 19950511T0000Z -p 19950521T0000Z '
            '-p 19950601T0000Z -p 19950611T0000Z -p 19950621T0000Z '
            '-p 19950701T0000Z -p 19950711T0000Z -p 19950721T0000Z '
            '-p 19950801T0000Z -p 19950811T0000Z -p 19950821T0000Z '
            '-p 19950901T0000Z -p 19950911T0000Z -p 19950921T0000Z '
            '-p 19951001T0000Z -p 19951011T0000Z -p 19951021T0000Z '
            '-p 19951101T0000Z -p 19951111T0000Z -p 19951121T0000Z '
            '-p 19951201T0000Z -p 19951211T0000Z -p 19951221T0000Z '
            '-s [environment]OZONE_ANCIL=ancil1990file'
        ]
        self.assertListEqual(mock_exec.mock_calls,
                             [mock.call(l) for l in expected_cmds])

    @mock.patch('retrieve_ozone_data.subprocess.check_output')
    def test_shell_cmd(self, mock_shell):
        '''Test call to subprocess to execute shell commands'''
        mock_shell.return_value = 'My Output!'
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            rval = retrieve_ozone_data.shell_cmd('run this command')

        self.assertEqual(rval, 0)
        self.assertIn(mock.call('[SUBPROCESS] My Output!'),
                      mock_out.write.mock_calls)
        mock_shell.assert_called_once_with(
            ['run', 'this', 'command'],
            stderr=retrieve_ozone_data.subprocess.STDOUT,
            universal_newlines=True,
            cwd=os.getcwd()
        )

    def test_shell_cmd_fail(self):
        '''Test call to subprocess to execute shell commands - fail'''
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            rval = retrieve_ozone_data.shell_cmd('run this command')

        self.assertNotEqual(rval, 0)
        self.assertIn('[SUBPROCESS] No such file or directory',
                      str(mock_out.write.mock_calls[0]))


class OzoneMainTests(unittest.TestCase):
    '''Unit tests for the main function'''
    def setUp(self):
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19950101T0000Z'
        os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT'] = '19900901T0000Z'
        os.environ['DATAM'] = 'History_Data'
        os.environ['OZONE_SHARE'] = ''
        os.environ['RUNID'] = 'RUNID'
        os.environ['SOURCE_STREAM'] = 'p4'
        os.environ['CYLC_SUITE_NAME'] = 'u-aa000'
        os.environ['UMTASK'] = 'coupled'
        os.environ['OZONE_ANCIL'] = 'ancilfile'
        os.environ['STASHCODES'] = '16203'
        os.environ['SECONDARY_ARCHIVE'] = 'arch2path'

    def tearDown(self):
        pass

    @mock.patch('retrieve_ozone_data.link_sourcefiles',
                return_value=True)
    @mock.patch('retrieve_ozone_data.OneYear')
    @mock.patch('retrieve_ozone_data.get_archived_data')
    def test_main(self, mock_arch, mock_data, mock_link):
        '''Test main function'''
        mock_data().missing_months = []
        mock_arch.return_value = mock_data()
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.main()

        self.assertListEqual(mock_link.mock_calls,
                             [mock.call(1994, False), mock.call(1993, False)])
        self.assertListEqual(mock_arch.mock_calls, [])
        self.assertIn(mock.call('\n[INFO] Proceeding to redistribution with '
                                '24 months of data'),
                      mock_out.write.mock_calls)

    @mock.patch('retrieve_ozone_data.link_sourcefiles',
                return_value=False)
    @mock.patch('retrieve_ozone_data.OneYear')
    @mock.patch('retrieve_ozone_data.get_archived_data')
    @mock.patch('retrieve_ozone_data.skip_redistribution')
    def test_main_first_cycle(self, mock_skip, mock_arch, mock_data, mock_link):
        '''Test main function'''
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19900101T0000Z'
        os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT'] = '19900101T0000Z'
        mock_data().missing_months = list(range(1, 13))
        mock_arch.return_value = mock_data()
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.main()

        self.assertListEqual(mock_link.mock_calls,
                             [mock.call(1989, True), mock.call(1988, True)])
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call(mock_data(1994), None, 1),
                              mock.call(mock_data(1993), 'arch2path', 2),
                              mock.call(mock_data(1994), None, 1),
                              mock.call(mock_data(1993), 'arch2path', 2)])
        mock_skip.assert_called_once_with()

        self.assertIn(mock.call('\n[INFO] Start of simulation - '
                                'no redistribution required'),
                      mock_out.write.mock_calls)


    @mock.patch('retrieve_ozone_data.link_sourcefiles',
                return_value=True)
    @mock.patch('retrieve_ozone_data.OneYear')
    @mock.patch('retrieve_ozone_data.get_archived_data')
    @mock.patch('retrieve_ozone_data.skip_redistribution')
    def test_main_4months(self, mock_skip, mock_arch, mock_data, mock_link):
        '''Test main function - Mid-year start'''
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19910101T0000Z'
        mock_1990 = mock.Mock()
        mock_1989 = mock.Mock()
        mock_1990.missing_months = list(range(1, 9))
        mock_1989.missing_months = list(range(1, 13))
        mock_data.side_effect = [mock_1990, mock_1989]
        mock_arch.side_effect = [mock_1990, mock_1990, mock_1989, mock_1989]

        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.main()

        self.assertListEqual(mock_link.mock_calls,
                             [mock.call(1990, False), mock.call(1989, False)])
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call(mock_1990, None, 1),
                              mock.call(mock_1990, 'arch2path', 2),
                              mock.call(mock_1989, None, 1),
                              mock.call(mock_1989, 'arch2path', 2)])
        mock_skip.assert_called_once_with()

        self.assertIn(mock.call('\n[INFO] Start of simulation - '
                                'no redistribution required'),
                      mock_out.write.mock_calls)

    @mock.patch('retrieve_ozone_data.link_sourcefiles',
                return_value=True)
    @mock.patch('retrieve_ozone_data.OneYear')
    @mock.patch('retrieve_ozone_data.get_archived_data')
    def test_main_16months(self, mock_arch, mock_data, mock_link):
        '''Test main function - Mid-year start'''
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19920101T0000Z'
        mock_1991 = mock.Mock()
        mock_1990 = mock.Mock()
        mock_1991.missing_months = []
        mock_1990.missing_months = [1, 2, 3, 4, 5, 6, 7, 8]
        mock_data.side_effect = [mock_1991, mock_1990]
        mock_arch.side_effect = [mock_1990, mock_1990]
        with mock.patch('retrieve_ozone_data.sys.stdout') as mock_out:
            retrieve_ozone_data.main()

        self.assertListEqual(mock_link.mock_calls,
                             [mock.call(1991, False), mock.call(1990, False)])
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call(mock_1990, None, 1),
                              mock.call(mock_1990, 'arch2path', 2)])

        self.assertIn(mock.call('\n[INFO] Proceeding to redistribution with '
                                '16 months of data'),
                      mock_out.write.mock_calls)

    @mock.patch('retrieve_ozone_data.link_sourcefiles',
                return_value=True)
    @mock.patch('retrieve_ozone_data.OneYear')
    def test_main_missing_data(self, mock_data, mock_link):
        '''Test main function - Mid-year start'''
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19910101T0000Z'
        mock_data().missing_months = list(range(1, 11))
        with self.assertRaises(retrieve_ozone_data.
                               OzoneMissingDataError) as exc:
            retrieve_ozone_data.main()
        self.assertTrue('Required data since NRun not found on disk: '
                        in str(exc.exception))
        self.assertListEqual(mock_link.mock_calls,
                             [mock.call(1990, False)])
        self.assertTrue('Year: 1990 Months: 9,10'
                        in str(exc.exception))


class OzoneOneYearTests(unittest.TestCase):
    '''Unit tests for the OneYear object'''
    def setUp(self):
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19950101T0000Z'
        os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT'] = '19900901T0000Z'
        os.environ['MODEL_DATA_LINK'] = ''
        os.environ['DATAM'] = ''
        os.environ['OZONE_SHARE'] = os.path.dirname(__file__)
        os.environ['RUNID'] = 'RUNID'
        os.environ['SOURCE_STREAM'] = 'p4'
        os.environ['CYLC_SUITE_NAME'] = ''
        os.environ['UMTASK'] = ''
        os.environ['OZONE_ANCIL'] = ''
        os.environ['STASHCODES'] = '16203'
        retrieve_ozone_data.setup_environment()
        self.env = retrieve_ozone_data.ENV
        self.year1998 = retrieve_ozone_data.OneYear(1998)

    def tearDown(self):
        pass

    def test_oneyear_instantiation(self):
        ''' Test creation of a OneYear object '''
        self.assertIsInstance(self.year1998, retrieve_ozone_data.OneYear)
        self.assertListEqual(self.year1998._fields, ['m01s16i203'])
        # Single data point in sample data is Dec 1988
        self.assertListEqual(self.year1998.missing_months,
                             [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertFalse(self.year1998.complete_year)

    def test_oneyear_wrong_year(self):
        ''' Test exception raised for no data available '''
        file1998 = os.path.join(os.getenv('OZONE_SHARE'), 'RUNIDa.p41998.pp')
        file1950 = os.path.join(os.getenv('OZONE_SHARE'), 'RUNIDa.po1950.pp')
        shutil.copy(file1998, file1950)
        with self.assertRaises(retrieve_ozone_data.
                               OzoneMissingDataError) as exc:
            _ = retrieve_ozone_data.OneYear(1950)
        os.remove(file1950)
        self.assertTrue('for incorrect year' in str(exc.exception))

    def test_oneyear_mismatch(self):
        '''Test exception raised for mismatched data on different cubes'''
        self.year1998._months = [False] * 10 + [True] * 2
        with self.assertRaises(retrieve_ozone_data.
                               OzoneMissingDataError) as exc:
            self.year1998.load_data()
        self.assertTrue('Mismatch in data points' in str(exc.exception))

    @mock.patch('retrieve_ozone_data.iris')
    @mock.patch('retrieve_ozone_data.OneYear.check_time_coords')
    def test_load_data(self, mock_time, mock_iris):
        '''Test load_data method'''
        mock_iris.load.side_effect = [['cube1'], ['cube2']]
        self.year1998.load_data()

        source = os.path.join(os.path.dirname(__file__), '*a.??1998*.pp')
        mock_iris.load.assert_called_once_with(source, constraints=mock.ANY)
        self.assertListEqual(mock_iris.AttributeConstraint.mock_calls,
                             [mock.call(time=mock.ANY),
                              mock.call(STASH='m01s16i203')])
        mock_time.assert_called_once_with('cube1')

    @mock.patch('retrieve_ozone_data.iris')
    @mock.patch('retrieve_ozone_data.OneYear.check_time_coords')
    def test_load_data_error(self, mock_time, mock_iris):
        '''Test load_data method - error'''
        mock_iris.load.side_effect = [OSError]
        with self.assertRaises(retrieve_ozone_data.
                               OzoneSourceNotFoundError) as exc:
            self.year1998.load_data()

        source = os.path.join(os.path.dirname(__file__), '*a.??1998*.pp')
        mock_iris.load.assert_called_once_with(source, constraints=mock.ANY)
        self.assertListEqual(mock_iris.AttributeConstraint.mock_calls,
                             [mock.call(time=mock.ANY),
                              mock.call(STASH='m01s16i203')])
        self.assertEqual(len(mock_time.mock_calls), 0)
        self.assertTrue('No files found matching "{}"'.format(source)
                        in str(exc.exception))


if __name__ == '__main__':
    unittest.main(buffer=True)
