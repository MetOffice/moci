#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    unicicles.py

DESCRIPTION
   Unicicles post processing application
'''

import os
import re

from collections import OrderedDict

import control
import utils
import nlist
import suite
import timer


class UniciclesPostProc(control.RunPostProc):
    '''
    Methods and properties specific to the UniCiCles (ice sheet model)
    post processing application.
    '''
    def __init__(self, input_nl='uniciclespp.nl'):
        '''
        Initialise Unicicles Postprocessing:
            Import namelist: unicicles_pp
            Check WORK and SHARE directories exist
        '''
        self.naml = nlist.load_namelist(input_nl)
        self.date_regex = re.compile(r'.*_(\d{8}-)?(\d{8})_.*')

        if self.runpp:
            self.share = self._directory(self.naml.unicicles_pp.share_directory,
                                         'UNICICLES SHARE')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)

            cycle_length = str(self.naml.unicicles_pp.cycle_length)
            start_cycle = utils.add_period_to_date(
                self.suite.cyclepoint.endcycle['intlist'], '-' + cycle_length
                )
            self.current_cycle = utils.CylcCycle(cyclepoint=start_cycle,
                                                 cycleperiod=cycle_length)

            # Initialise debug mode - calling base class method
            self._debug_mode(debug=self.naml.unicicles_pp.debug)

    @property
    def runpp(self):
        '''
        Logical - Run postprocessing for Unicicles
        Set via the unicicles_pp namelist
        '''
        return self.naml.unicicles_pp.pp_run

    @property
    def methods(self):
        '''
        Returns a dictionary of methods available for this model to the
        main program
        '''
        return OrderedDict([('do_archive', True),
                            ('do_delete', True)])

    @property
    def template_to_delete(self):
        '''
        Regular expressions to match Intermediate files used in the coupling.
        Files produced during the current cycle should always be deleted.
        '''
        return [r'^{}a.da_\d{{8}}_00-pre_ice$'.format(self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_bisicles-icecouple-(A|Gr)IS\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_calv-(A|Gr)IS\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_orog-(hi|lo)-(A|Gr)IS\.anc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_orog-lo-(A|Gr)IS\.anc.xml$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_orog-lo\.anc$'.
                format('unicicles', self.suite.prefix),
                r'^{}o_\d*[dmy]_\d{{8}}_\d{{8}}_isf_T[0-9_-]*.nc$'.
                format(self.suite.prefix)]

    @property
    def template_to_archive(self):
        '''
        Regular expressions to match files to be archived.
        '''
        return [r'^{}c_\d{{8}}_bisicles-(A|Gr)IS_restart\.hdf5$'.
                format(self.suite.prefix),
                r'^{}c_\d{{8}}_glint-(A|Gr)IS_restart\.nc$'.
                format(self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_calving-(A|Gr)IS\.hdf5$'.
                format('bisicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_plot-(A|Gr)IS\.hdf5$'.
                format('bisicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_nemo-icecouple-AIS\.hdf5$'.
                format('bisicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_atmos-icecouple\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_nemo-bathy-isf\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_bisicles-icecouple\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_calving\.nc$'.
                format('unicicles', self.suite.prefix),
                r'^{0}_{1}c_\d*[dmy]_\d{{8}}-\d{{8}}_nemo-icecouple\.nc$'.
                format('unicicles', self.suite.prefix)]

    def select_file(self, fname, thiscycle=False):
        '''
        Return True to indicate file should be selected for archive
        or delete.
        Ignore files dated at or before initial cycle point.
        Select file dated during this cycle only by default.

        Optional Arguments:
          <type bool> thiscycle.  Default=False
              If True: Select file dated between start and end of current cycle
              If False: Select file dated at or before end of current cycle
        '''
        file_enddate = self.date_regex.match(fname).group(2)

        # Ignore any files dated up to the initial cycle point
        select_start = file_enddate > ''.join(
            [str(x).zfill(2) for x in self.suite.initpoint[:3]]
        )
        
        # Ignore any files due to be selected in subsequent tasks
        if thiscycle is True:
            # Ignore files dated at or after current cycle end
            select_end = file_enddate < self.current_cycle.endcycle['iso'][:8]
        else:
            # Ignore files ending after current cycle end
            select_end = file_enddate <= self.current_cycle.endcycle['iso'][:8]

        return select_start and select_end

    @timer.run_timer
    def do_archive(self, finalcycle=False, skiptimer=False):
        '''
        Archive files.
        Optional Arguments:
           <type bool> finalcycle.  When true run  final cycle processing
           <type bool> skiptimer.   When true, skip @run_timer (recursive) 
        '''
        normalcycle = not finalcycle
        archive_files = []
        for pattern in self.template_to_archive:
            # Get files to archive
            archive_files += utils.get_subset(self.share, pattern)

        # Select only files upto and including the START of the
        # current cycle
        archive_files = [f for f in set(archive_files) if
                         self.select_file(f, thiscycle=normalcycle)]

        arch_success = []
        for archfile in utils.add_path(archive_files, self.share):
            rcode = self.suite.archive_file(archfile)
            if rcode == 0:
                utils.log_msg('Archive successful: ' + archfile, level='OK')
                arch_success.append(archfile)
            else:
                utils.log_msg('Failed to archive file: {}. '.format(archfile) +
                              'Will try again later.', level='WARN')

        if arch_success and normalcycle:
            self.do_delete(filelist=arch_success)

        if self.suite.finalcycle and normalcycle:
            # Archive any files remaining at the final cycle point
            utils.log_msg('Running do_archive on final cycle...')
            self.do_archive(finalcycle=True, skiptimer=True)

    @timer.run_timer
    def do_delete(self, filelist=None):
        '''
        Delete files.

        Optional argument:
           filelist <type list> List of archived files, including path
        '''
        msg = 'Selecting files for deletion...\n'
        level = 'INFO'
        if filelist is None:
            # Find files to delete based on template_to_delete
            filelist = []
            for pattern in self.template_to_delete:
                filelist += utils.get_subset(self.share, pattern)

            # Ignore any files from any future cycles
            filelist = [f for f in set(filelist) if self.select_file(f)]

            if utils.get_debugmode():
                msg += 'Would delete intermediate file(s): \n\t'
                level = 'DEBUG'
            else:
                msg += 'Deleting intermediate file(s): \n\t'
                utils.remove_files(filelist, self.share)

        elif filelist:
            # Delete pre-compiled list of archived files
            if utils.get_debugmode():
                msg += 'Would delete archived file(s): \n\t'
                level = 'DEBUG'
                for delfile in filelist:
                    # Append "ARCHIVED" suffix to files, rather than deleting
                    os.rename(delfile, delfile.rstrip('_ARCHIVED') +
                              '_ARCHIVED')
            else:
                msg += 'Deleting archived file(s): \n\t'
                utils.remove_files(filelist)

        utils.log_msg(msg + '\n\t'.join(filelist), level=level)


INSTANCE = ('uniciclespp.nl', UniciclesPostProc)


if __name__ == '__main__':
    pass
