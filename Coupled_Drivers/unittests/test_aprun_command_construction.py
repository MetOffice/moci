#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_aprun_command_construction.py

DESCRIPTION
    Tests construction of aprun command.
'''
import unittest
import unittest.mock as mock
import os
from io import StringIO

import common
import dr_env_lib.env_lib
import um_driver
import nemo_driver
import xios_driver
import jnr_driver

#pylint: disable=protected-access

class TestCommon(unittest.TestCase):
    ''' Tests for common.py '''

    def test_set_aprun_options(self):
        ''' Test common.set_aprun_options() returns a string with the correct
        options and values '''
        nproc = "77"
        nodes = "3"
        ompthr = "1"
        hyperthreads = "1"

        for ss in [False, True]:
            if ss:
                expected_output = \
                    "-ss -n 77 -N 26 -S 13 -d 1 -j 1 "\
                        "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"
            else:
                expected_output = \
                    "-n 77 -N 26 -S 13 -d 1 -j 1 "\
                        "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"

            opts = common.set_aprun_options(\
                nproc, nodes, ompthr, hyperthreads, ss)

            self.assertEqual(opts, expected_output)

    def test_set_aprun_options_single_proc(self):
        ''' Test common.set_aprun_options() returns a string with the correct
        options and values when nproc == 1'''
        nproc = "1"
        nodes = "1"
        ompthr = "1"
        hyperthreads = "1"
        ss = False

        expected_output = \
            "-n 1 -N 1 -S 1 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"

        opts = common.set_aprun_options(\
            nproc, nodes, ompthr, hyperthreads, ss)

        self.assertEqual(opts, expected_output)

class TestUMDriver(unittest.TestCase):
    ''' Tests for um_driver.py '''

    def setUp(self):
        ''' Set up for UM driver tests '''
        self.um_envar_dict = {
            'UM_ATM_NPROCX': "",
            'UM_ATM_NPROCY': "",
            'VN': "",
            'UMDIR': "",
            'ATMOS_EXEC': "",
            'ATMOS_LINK': "um.exe"
        }

    def _set_um_envar_driver(self):
        ''' Sets required environment variables for driver aprun command
        construction '''
        self.um_envar_dict.update({
            'OMPTHR_ATM': "1",
            'ATMOS_NODES': "8",
            'HYPERTHREADS': "1"
        })

    def _set_um_envar_suite(self):
        ''' Sets required environment variables for suite aprun command
        construction '''
        self.um_envar_dict.update({
            'ROSE_LAUNCHER_PREOPTS_UM': "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"
        })

    def _get_um_envar(self):
        ''' Returns envar object '''
        um_envar = dr_env_lib.env_lib.LoadEnvar()

        for key in self.um_envar_dict:
            um_envar.add(key, self.um_envar_dict[key])

        return um_envar

    def test_set_launcher_command_suite_construction(self):
        ''' Test UM driver _set_launcher_command() returns a string with the
        correct values if ROSE_LAUNCHER_PREOPTS_UM is set as an environment
        variable regardless of the launcher '''
        launcher = ""
        self._set_um_envar_suite()
        um_envar = self._get_um_envar()

        # In UM driver NPROC is calculated and added during _setup_executable()
        um_envar.add('NPROC', "288")

        cmd = um_driver._set_launcher_command(launcher, um_envar)

        expected_output_cmd = \
            "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./um.exe"
        expected_output_preopts = \
            "'-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_UM in um_envar
        self.assertTrue(um_envar.contains("ROSE_LAUNCHER_PREOPTS_UM"))
        self.assertEqual(um_envar["ROSE_LAUNCHER_PREOPTS_UM"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_aprun(self):
        ''' Test UM driver _set_launcher_command() returns a string with the
        correct options and values if launcher is aprun and driver aprun
        command construction environment variables are set, and that
        ROSE_LAUNCHER_PREOPTS is added to the envar dictionary '''
        launcher = "aprun"
        self._set_um_envar_driver()
        um_envar = self._get_um_envar()

        # In UM driver NPROC is calculated and added during _setup_executable()
        um_envar.add('NPROC', "288")
        um_envar.add('ROSE_LAUNCHER_PREOPTS_UM', "unset")
        cmd = um_driver._set_launcher_command(launcher, um_envar)

        expected_output_cmd = \
            "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./um.exe"
        expected_output_preopts = \
            "'-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_UM in um_envar
        self.assertTrue(um_envar.contains("ROSE_LAUNCHER_PREOPTS_UM"))
        self.assertEqual(um_envar["ROSE_LAUNCHER_PREOPTS_UM"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_not_aprun(self):
        ''' Test UM driver _set_launcher_command() returns a string containing
        the executable link only when launcher is not aprun and
        ROSE_LAUNCHER_PREOPTS_UM is not set '''
        launcher = "mpirun"
        self._set_um_envar_driver()
        um_envar = self._get_um_envar()
        um_envar.add('ROSE_LAUNCHER_PREOPTS_UM', "unset")
        # In UM driver NPROC is calculated and added during _setup_executable()
        um_envar.add('NPROC', "288")

        cmd = um_driver._set_launcher_command(launcher, um_envar)

        expected_output_cmd = " ./um.exe"
        expected_output_preopts = "''"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_UM in um_envar
        self.assertTrue(um_envar.contains("ROSE_LAUNCHER_PREOPTS_UM"))
        self.assertEqual(um_envar["ROSE_LAUNCHER_PREOPTS_UM"], \
            expected_output_preopts)

class TestNEMODriver(unittest.TestCase):
    ''' Tests for nemo_driver.py '''

    def setUp(self):
        ''' Set up for NEMO driver tests '''
        self.nemo_envar_dict = {
            'OCEAN_EXEC': "",
            'NEMO_IPROC': "",
            'NEMO_JPROC': "",
            'NEMO_NPROC': "77",
            'CALENDAR': "",
            'MODELBASIS': "",
            'TASKSTART': "",
            'TASKLENGTH': "",
            'NEMO_VERSION': "",
            'OCEAN_LINK': "nemo.exe"
        }

    def _set_nemo_envar_driver(self):
        ''' Sets required environment variables for driver aprun command
        construction '''
        self.nemo_envar_dict.update({
            'OMPTHR_OCN': "1",
            'OCEAN_NODES': "3",
            'OHYPERTHREADS': "1"
        })

    def _set_nemo_envar_suite(self):
        ''' Sets required environment variables for suite aprun command
        construction '''
        self.nemo_envar_dict.update({
            'ROSE_LAUNCHER_PREOPTS_NEMO': "-n 77 -N 26 -S 13 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"
        })

    def _get_nemo_envar(self):
        ''' Returns envar object '''
        nemo_envar = dr_env_lib.env_lib.LoadEnvar()

        for key in self.nemo_envar_dict:
            nemo_envar.add(key, self.nemo_envar_dict[key])

        return nemo_envar

    def test_set_launcher_command_suite_construction(self):
        ''' Test NEMO driver _set_launcher_command() returns a string with the
        correct values if ROSE_LAUNCHER_PREOPTS_NEMO is set as an environment
        variable regardless of the launcher '''
        launcher = ""
        self._set_nemo_envar_suite()
        nemo_envar = self._get_nemo_envar()

        cmd = nemo_driver._set_launcher_command(launcher, nemo_envar)

        expected_output_cmd = \
            "-n 77 -N 26 -S 13 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./nemo.exe"
        expected_output_preopts = \
            "'-n 77 -N 26 -S 13 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_NEMO in nemo_envar
        self.assertTrue(nemo_envar.contains("ROSE_LAUNCHER_PREOPTS_NEMO"))
        self.assertEqual(nemo_envar["ROSE_LAUNCHER_PREOPTS_NEMO"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_aprun(self):
        ''' Test NEMO driver _set_launcher_command() returns a string with the
        correct options and values if launcher is aprun and driver aprun
        command construction environment variables are set, and that
        ROSE_LAUNCHER_PREOPTS_NEMO is added to the envar dictionary '''
        launcher = "aprun"
        self._set_nemo_envar_driver()
        nemo_envar = self._get_nemo_envar()
        nemo_envar.add('ROSE_LAUNCHER_PREOPTS_NEMO', "unset")
        cmd = nemo_driver._set_launcher_command(launcher, nemo_envar)

        expected_output_cmd = \
            "-n 77 -N 26 -S 13 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./nemo.exe"
        expected_output_preopts = \
            "'-n 77 -N 26 -S 13 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_NEMO in nemo_envar
        self.assertTrue(nemo_envar.contains("ROSE_LAUNCHER_PREOPTS_NEMO"))
        self.assertEqual(nemo_envar["ROSE_LAUNCHER_PREOPTS_NEMO"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_not_aprun(self):
        ''' Test NEMO driver _set_launcher_command() returns a string
        containing the executable link only when launcher is not aprun and
        ROSE_LAUNCHER_PREOPTS_NEMO is not set '''
        launcher = "mpirun"
        self._set_nemo_envar_driver()
        nemo_envar = self._get_nemo_envar()
        nemo_envar.add('ROSE_LAUNCHER_PREOPTS_NEMO', "unset")
        cmd = nemo_driver._set_launcher_command(launcher, nemo_envar)

        expected_output_cmd = " ./nemo.exe"
        expected_output_preopts = "''"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_NEMO in nemo_envar
        self.assertTrue(nemo_envar.contains("ROSE_LAUNCHER_PREOPTS_NEMO"))
        self.assertEqual(nemo_envar["ROSE_LAUNCHER_PREOPTS_NEMO"], \
            expected_output_preopts)

class TestJNRDriver(unittest.TestCase):
    ''' Tests for jnr_driver.py '''

    def setUp(self):
        ''' Set up for JNR driver tests '''
        self.jnr_envar_dict = {
            'UM_ATM_NPROCX_JNR': "",
            'UM_ATM_NPROCY_JNR': "",
            'ATMOS_EXEC_JNR': "",
            'ATMOS_LINK_JNR': "jnr.exe"
        }

    def _set_jnr_envar_driver(self):
        ''' Sets required environment variables for driver aprun command
        construction '''
        self.jnr_envar_dict.update({
            'OMPTHR_JNR': "1",
            'JNR_NODES': "8",
            'HYPERTHREADS': "1"
        })

    def _set_jnr_envar_suite(self):
        ''' Sets required environment variables for suite aprun command
        construction '''
        self.jnr_envar_dict.update({
            'ROSE_LAUNCHER_PREOPTS_JNR': "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"
        })

    def _get_jnr_envar(self):
        ''' Returns envar object '''
        jnr_envar = dr_env_lib.env_lib.LoadEnvar()

        for key in self.jnr_envar_dict:
            jnr_envar.add(key, self.jnr_envar_dict[key])

        return jnr_envar

    def test_set_launcher_command_suite_construction(self):
        ''' Test JNR driver _set_launcher_command() returns a string with the
        correct values if ROSE_LAUNCHER_PREOPTS_JNR is set as an environment
        variable regardless of the launcher '''
        launcher = ""
        self._set_jnr_envar_suite()
        jnr_envar = self._get_jnr_envar()

        cmd = jnr_driver._set_launcher_command(launcher, jnr_envar)

        expected_output_cmd = \
            "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./jnr.exe"
        expected_output_preopts = \
            "'-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_JNR in jnr_envar
        self.assertTrue(jnr_envar.contains("ROSE_LAUNCHER_PREOPTS_JNR"))
        self.assertEqual(jnr_envar["ROSE_LAUNCHER_PREOPTS_JNR"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_aprun(self):
        ''' Test JNR driver _set_launcher_command() returns a string with the
        correct options and values if launcher is aprun and driver aprun
        command construction environment variables are set, and that
        ROSE_LAUNCHER_PREOPTS_JNR is added to the envar dictionary '''
        launcher = "aprun"
        self._set_jnr_envar_driver()
        jnr_envar = self._get_jnr_envar()

        # In JNR driver NPROC is calculated and added during
        # _setup_executable()
        jnr_envar.add('ROSE_LAUNCHER_PREOPTS_JNR', "unset")
        jnr_envar.add('NPROC_JNR', "288")

        cmd = jnr_driver._set_launcher_command(launcher, jnr_envar)

        expected_output_cmd = \
            "-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./jnr.exe"
        expected_output_preopts = \
            "'-n 288 -N 36 -S 18 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_JNR in jnr_envar
        self.assertTrue(jnr_envar.contains("ROSE_LAUNCHER_PREOPTS_JNR"))
        self.assertEqual(jnr_envar["ROSE_LAUNCHER_PREOPTS_JNR"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_not_aprun(self):
        ''' Test JNR driver _set_launcher_command() returns a string containing
        the executable link only when launcher is not aprun and
        ROSE_LAUNCHER_PREOPTS_JNR is not set '''
        launcher = "mpirun"
        self._set_jnr_envar_driver()
        jnr_envar = self._get_jnr_envar()
        jnr_envar.add('ROSE_LAUNCHER_PREOPTS_JNR', "unset")
        cmd = jnr_driver._set_launcher_command(launcher, jnr_envar)

        expected_output_cmd = " ./jnr.exe"
        expected_output_preopts = "''"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_JNR in jnr_envar
        self.assertTrue(jnr_envar.contains("ROSE_LAUNCHER_PREOPTS_JNR"))
        self.assertEqual(jnr_envar["ROSE_LAUNCHER_PREOPTS_JNR"], \
            expected_output_preopts)

class TestXIOSDriver(unittest.TestCase):
    ''' Tests for xios_driver.py '''

    def setUp(self):
        ''' Set up for XIOS driver tests '''
        self.xios_envar_dict = {
            'XIOS_EXEC': "xios_exec.exe",
            'models': "",
            'XIOS_LINK': "xios.exe"
        }
        self.common_env_dict = {'models': []}

    def tearDown(self):
        ''' Clean-up after XIOS driver tests '''
        try:
            os.unlink(self.xios_envar_dict['XIOS_LINK'])
        except FileNotFoundError:
            pass

    def _set_xios_nproc(self, nproc="6"):
        ''' Sets nproc in environment variables'''
        self.xios_envar_dict.update({
            'XIOS_NPROC': nproc
        })

    def _set_xios_envar_driver(self, nproc="6"):
        ''' Sets required environment variables for driver aprun command
        construction '''
        self.xios_envar_dict.update({
            'XIOS_NPROC': nproc,
            'XIOS_NODES': "1"
        })

    def _set_xios_envar_suite(self, nproc="6"):
        ''' Sets required environment variables for suite aprun command
        construction '''
        self.xios_envar_dict.update({
            'XIOS_NPROC': nproc,
            'ROSE_LAUNCHER_PREOPTS_XIOS': "-ss -n 6 -N 6 -S 3 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1"
        })

    def _get_xios_envar(self):
        ''' Returns envar object '''
        xios_envar = dr_env_lib.env_lib.LoadEnvar()

        for key in self.xios_envar_dict:
            xios_envar.add(key, self.xios_envar_dict[key])

        return xios_envar

    @mock.patch("xios_driver._update_iodef", return_value=None)
    def test_setup_executable_none(self, _):
        ''' Tests _setup_executable() exits with error when no
        aprun command variables are set '''
        # Set default nproc
        self._set_xios_nproc()

        with mock.patch('sys.stdout', new=StringIO()) as mock_out, \
            mock.patch('sys.stderr', new=StringIO()), \
            mock.patch.dict(os.environ, self.xios_envar_dict):
            xios_driver._setup_executable(self.common_env_dict)

            self.assertRegex(mock_out.getvalue(), \
                "ROSE_LAUNCHER_PREOPTS_XIOS doesn't exist")

    @mock.patch("xios_driver._update_iodef", return_value=None)
    def test_setup_executable_suite(self, _):
        ''' Tests _setup_executable() loads suite aprun command variables '''
        self._set_xios_envar_suite()

        with mock.patch('sys.stdout', new=StringIO()) as mock_out, \
            mock.patch.dict(os.environ, self.xios_envar_dict):
            xios_envar = xios_driver._setup_executable(self.common_env_dict)

            # Assert ROSE_LAUNCHER_PREOPTS_XIOS has been used and is in
            # xios_envar
            self.assertNotRegex(mock_out.getvalue(), \
                "ROSE_LAUNCHER_PREOPTS_XIOS doesn't exist")
            self.assertTrue(xios_envar.contains("ROSE_LAUNCHER_PREOPTS_XIOS"))
            self.assertEqual(xios_envar["ROSE_LAUNCHER_PREOPTS_XIOS"],
                             self.xios_envar_dict['ROSE_LAUNCHER_PREOPTS_XIOS'])

    @mock.patch("xios_driver._update_iodef", return_value=None)
    def test_setup_executable_driver(self, _):
        ''' Tests _setup_executable() loads driver aprun command variables '''
        self._set_xios_envar_driver()

        with mock.patch('sys.stdout', new=StringIO()) as mock_out, \
            mock.patch.dict(os.environ, self.xios_envar_dict):
            xios_envar = xios_driver._setup_executable(self.common_env_dict)

            # Assert ROSE_LAUNCHER_PREOPTS_XIOS has not been used and is not
            # yet in xios_envar
            self.assertRegex(mock_out.getvalue(), \
                "ROSE_LAUNCHER_PREOPTS_XIOS doesn't exist")
            self.assertEqual(xios_envar["ROSE_LAUNCHER_PREOPTS_XIOS"],
                             "unset")

    def test_set_launcher_command_suite_construction(self):
        ''' Test XIOS driver _set_launcher_command() returns a string with the
        correct values if ROSE_LAUNCHER_PREOPTS_XIOS is set as an environment
        variable regardless of the launcher '''
        launcher = ""
        self._set_xios_envar_suite()
        xios_envar = self._get_xios_envar()

        cmd = xios_driver._set_launcher_command(launcher, xios_envar)

        expected_output_cmd = \
            "-ss -n 6 -N 6 -S 3 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./xios.exe"
        expected_output_preopts = \
            "'-ss -n 6 -N 6 -S 3 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_XIOS in xios_envar
        self.assertTrue(xios_envar.contains("ROSE_LAUNCHER_PREOPTS_XIOS"))
        self.assertEqual(xios_envar["ROSE_LAUNCHER_PREOPTS_XIOS"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_attached_mode(self):
        ''' Test XIOS driver _set_launcher_command() returns an empty string
        when nproc set to 0 (so set to run in attached mode) '''
        launcher = "aprun"
        nproc = "0"
        self._set_xios_envar_driver(nproc)
        xios_envar = self._get_xios_envar()

        cmd = xios_driver._set_launcher_command(launcher, xios_envar)

        expected_output_cmd = ""

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_XIOS not in xios_envar
        self.assertFalse(xios_envar.contains("ROSE_LAUNCHER_PREOPTS_XIOS"))

    def test_set_launcher_command_driver_construction_aprun(self):
        ''' Test XIOS driver _set_launcher_command() returns a string with the
        correct options and values if launcher is aprun, nproc is not 0 and
        driver aprun command construction environment variables are set, and
        that ROSE_LAUNCHER_PREOPTS is added to the envar dictionary '''
        launcher = "aprun"
        self._set_xios_envar_driver()
        xios_envar = self._get_xios_envar()
        xios_envar.add('ROSE_LAUNCHER_PREOPTS_XIOS', "unset")
        cmd = xios_driver._set_launcher_command(launcher, xios_envar)

        expected_output_cmd = \
            "-ss -n 6 -N 6 -S 3 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1 ./xios.exe"
        expected_output_preopts = \
            "'-ss -n 6 -N 6 -S 3 -d 1 -j 1 "\
                "env OMP_NUM_THREADS=1 env HYPERTHREADS=1'"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_XIOS in xios_envar
        self.assertTrue(xios_envar.contains("ROSE_LAUNCHER_PREOPTS_XIOS"))
        self.assertEqual(xios_envar["ROSE_LAUNCHER_PREOPTS_XIOS"], \
            expected_output_preopts)

    def test_set_launcher_command_driver_construction_not_aprun(self):
        ''' Test XIOS driver _set_launcher_command() returns a string
        containing the executable link only when launcher is not aprun and
        ROSE_LAUNCHER_PREOPTS_UM is not set '''
        launcher = "mpirun"
        self._set_xios_envar_driver()
        xios_envar = self._get_xios_envar()
        xios_envar.add('ROSE_LAUNCHER_PREOPTS_XIOS', "unset")
        cmd = xios_driver._set_launcher_command(launcher, xios_envar)

        expected_output_cmd = " ./xios.exe"
        expected_output_preopts = "''"

        # Assert cmd string returned is as expected
        self.assertEqual(cmd, expected_output_cmd)

        # Assert ROSE_LAUNCHER_PREOPTS_XIOS in xios_envar
        self.assertTrue(xios_envar.contains("ROSE_LAUNCHER_PREOPTS_XIOS"))
        self.assertEqual(xios_envar["ROSE_LAUNCHER_PREOPTS_XIOS"], \
            expected_output_preopts)

if __name__ == '__main__':
    unittest.main()
