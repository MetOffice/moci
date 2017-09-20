#!/usr/bin/env python
# *****************************COPYRIGHT*******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT*******************************
"""
Module to contain all the classes derived from rose_ana.Analysis which can be
used to compare model output of various sorts to check that it matches.
"""
from rose.apps.rose_ana import AnalysisTask

import compare_nemo_solver_stat
import compare_utils

class RoseAnaRestartTask(AnalysisTask):
    """
    Base class for restart comparison rose_ana tasks.
    """
    def __init__(self, parent_app, task_options):
        """
        Initialise function for RoseAnaRestartTask class.
        """
        AnalysisTask.__init__(self, parent_app, task_options)
        self.list_errors = True
        self.stop_on_error = False
        self.save_memory = True
        self.passed = False

    def load_settings(self):
        """
        Load settings passed in through rose_ana task configuration files.
        """
        try:
            self.list_errors = self.options['list_errors'] == 'true'
        except KeyError:
            self.list_errors = True
        try:
            self.stop_on_error = self.options['stop_on_error'] == 'true'
        except KeyError:
            self.stop_on_error = False
        self.save_memory = True

    def write_out(self, msg):
        """
        Write output to rose_ana reporter object with prefix [INFO].
        """
        self.parent.reporter(msg + '\n', prefix='[INFO]')

    def write_error(self, msg):
        """
        Write output to rose_ana reporter object with prefix [ERROR].
        """
        self.parent.reporter(msg + '\n', prefix='[ERROR]')

    def write_both(self, msg):
        """
        Write output to rose_ana reporter object
        """
        self.write_out(msg)
        self.write_error(msg)

class NemoSolverStatComparison(RoseAnaRestartTask):
    """
    Analysis class for comparing norm values in NEMO solver.stat output files
    """
    def __init__(self, parent_app, task_options):
        """
        Initialise function for NemoSolverStatComparison class.
        """
        RoseAnaRestartTask.__init__(self, parent_app, task_options)
        self.solver_path1 = ''
        self.solver_path2 = ''
        self.solver_offset2 = 0
        self.passed = False

    def load_settings(self):
        """
        Load settings passed in through rose_ana task configuration files.
        """
        RoseAnaRestartTask.load_settings(self)
        self.solver_path1 = self.options['solver_path1']
        self.solver_path2 = self.options['solver_path2']
        self.solver_offset2 = int(self.options['solver_offset2'])

    def run_analysis(self):
        """
        Function called by rose_ana task to do comparison of NEMO
        solver.stat files
        """
        self.load_settings()
        msg1 = 'Comparing NEMO solver.stat files:\n'
        msg1 += 'file 1: {0}'.format(self.solver_path1)
        msg1 += 'file 2: {0}'.format(self.solver_path2)
        self.write_out(msg1)
        ret_val_solver = \
            compare_nemo_solver_stat.compare_solver_stat_files(
                self.solver_path1,
                self.solver_path2,
                self.list_errors,
                self.stop_on_error,
                self.solver_offset2,
                self)

        if ret_val_solver == 0:
            self.passed = True
        else:
            self.write_out('Mismatches found in solver.stat files.')

class NetCdfComparison(RoseAnaRestartTask):
    """
    Analysis class for comparing netcdf files.
    """
    def __init__(self, parent_app, task_options):
        """
        Initialise function for NetCdfComparison class.
        """
        RoseAnaRestartTask.__init__(self, parent_app, task_options)
        self.file1 = ''
        self.file2 = ''
        self.ignore_halos = False
        self.halo_size = 0
        self.ignore_variables = []
        self.model_name = ''

    def load_settings(self):
        """
        Load settings passed in through rose_ana task configuration files.
        """
        RoseAnaRestartTask.load_settings(self)
        self.file1 = self.options['netcdf_file1']
        self.file2 = self.options['netcdf_file2']

        try:
            self.ignore_halos = self.options['ignore_halos'] == 'true'
            self.halo_size = int(self.options['halo_size'])
        except KeyError:
            self.ignore_halos = False
            self.halo_size = 0

        try:
            self.ignore_variables = \
                [iv1 for iv1 in self.options['ignore_variables'].split(',')
                 if len(iv1) > 0]

        except KeyError:
            self.ignore_variables = []

        try:
            self.model_name = self.options['model_name']
        except KeyError:
            self.model_name = ''


    def run_analysis(self):
        """
        Function called by rose_ana task to do comparison of netcdf files.
        """
        self.load_settings()
        msg1 = 'Comparing NetCDF instantaneous files:\n'
        msg1 += 'file 1: {0}\n'.format(self.file1)
        msg1 += 'file 2: {0}\n'.format(self.file2)
        self.write_out(msg1)

        error_list1 = \
            compare_utils.compare_cube_list_files(self.file1,
                                                  self.file2,
                                                  self.stop_on_error,
                                                  self.ignore_halos,
                                                  self.halo_size,
                                                  self.ignore_variables,
                                                  self.save_memory,
                                                  self)
        if error_list1:
            msg1 = 'Mismatches found in {0} files\n'.format(self.model_name)
            self.write_both(msg1)
            compare_utils.print_cube_errors(self.model_name,
                                            error_list1,
                                            self)
        else:
            self.write_out('NetCDF files match!\n')
            self.passed = True



class NemoDiagnostic(NetCdfComparison):
    """
    Analysis class to compare NEMO diagnostic output files.
    """
    def run_analysis(self):
        """
        Function called by rose_ana task to do comparison of NEMO files.
        """
        self.load_settings()

        msg1 = 'Comparing NEMO diagnostic files:\n'
        msg1 += 'file 1: {0}\n'.format(self.file1)
        msg1 += 'file 2: {0}\n'.format(self.file2)
        self.write_out(msg1)

        error_list = \
            compare_utils.compare_netcdf_diagnostic_files(self.file1,
                                                          self.file2,
                                                          self.stop_on_error,
                                                          self)

        if len(error_list) > 0:
            self.write_both('Mismatches found in NEMO diagnostic files\n')
            compare_utils.print_cube_errors('NEMO diagnostic',
                                            error_list,
                                            self)
        else:
            self.write_out('Nemo diagnostic files match!\n')
            self.passed = True
