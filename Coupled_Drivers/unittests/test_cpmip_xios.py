#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''

import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import io
import os
import cpmip_xios

class TestDataMetricSetupNemo(unittest.TestCase):
    '''
    Check the setting up of XIOS for NEMO data metrics
    '''
    def setUp(self):
        '''
        Create an iodef file for test
        '''
        self.xml_file_name = 'iodef.xml'
        input_contents = 'iodef line 1\n' \
                         'variable id="using_server"\n' \
                         '\t  <variable id="print_file"           '  \
                         '     type="bool">false</variable>\n' \
                         'iodef line 4\n'
        with open(self.xml_file_name, 'w') as iodef_fh:
            iodef_fh.write(input_contents)

    def tearDown(self):
        '''
        Remove the iodef file at the end of test
        '''
        try:
            os.remove(self.xml_file_name)
        except FileNotFoundError:
            pass

    def test_update_iodef(self):
        '''
        Test the iodef file is updated correctly
        '''
        expected_output = 'iodef line 1\n' \
                          'variable id="using_server"\n' \
                          '\t  <variable id="print_file"           '  \
                          '     type="bool">true</variable>\n' \
                          'iodef line 4\n'

        cpmip_xios.data_metrics_setup_nemo()
        # check contents of new iodef.xml file
        with open(self.xml_file_name, 'r') as new_iodef_fh:
            new_iodef_contents = new_iodef_fh.read()
        self.assertEqual(new_iodef_contents, expected_output)
        self.assertFalse('iodef_out.xml' in os.listdir('.'))


class TestMeasureXIOSClient(unittest.TestCase):
    '''
    Test measurement of timings from XIOS client files
    '''
    @mock.patch('cpmip_xios.os.listdir', return_value=[])
    def test_no_files(self, mock_listdir):
        '''
        Test that the correct output and error messages are produced when
        no XIOS client files can be found
        '''
        expected_output = '[INFO] Measured timings for (0/0) XIOS clients\n'
        expected_error = '[WARN] Unable to find any XIOS client output files\n'

        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
                self.assertEqual(cpmip_xios.measure_xios_client_times(),
                                 (0.0, 0.0))
        self.assertEqual(patch_out.getvalue(), expected_output)
        self.assertEqual(patch_err.getvalue(), expected_error)

    @mock.patch('cpmip_xios.os.listdir', return_value=
                ['xios_client0.out',
                 'xios_client1.out',
                 'xios_client2.out'])
    @mock.patch('cpmip_xios.common.exec_subproc_timeout')
    def test_three_files(self, mock_exec_subproc, mock_listdir):
        '''
        Test that three files with no timeout give mean and max
        '''
        mock_exec_subproc.side_effect = [
            (0, '-> report : Performance report : total time spent for XIOS'
             ' : 100.0 s'),
            (0, '-> report : Performance report : total time spent for XIOS'
             ' : 10.0 s'),
            (0, '-> report : Performance report : total time spent for XIOS'
             ' : 1000.0 s')]
        expected_output = (370.0, 1000.0)
        with mock.patch('sys.stdout', new=io.StringIO()) as patch_output:
            self.assertEqual(cpmip_xios.measure_xios_client_times(),
                             expected_output)
        self.assertEqual(patch_output.getvalue(),
                         '[INFO] Measured timings for (3/3) XIOS clients\n')

    @mock.patch('cpmip_xios.os.listdir', return_value=
                ['xios_client0.out',
                 'xios_client1.out',
                 'xios_client2.out'])
    @mock.patch('cpmip_xios.common.exec_subproc_timeout')
    def test_one_timeout(self, mock_exec_subproc, mock_listdir):
        '''
        Test what happens if there is a timeout
        '''
        mock_exec_subproc.side_effect = [
            (0, '-> report : Performance report : total time spent for XIOS'
             ' : 100.0 s'),
            (1, None),
            (0, '-> report : Performance report : total time spent for XIOS'
             ' : 1000.0 s')]
        expected_output = (550.0, 1000.0)
        with mock.patch('sys.stdout', new=io.StringIO()) as patch_output:
            self.assertEqual(cpmip_xios.measure_xios_client_times(),
                             expected_output)
        self.assertEqual(patch_output.getvalue(),
                         '[INFO] Measured timings for (2/3) XIOS clients\n')
