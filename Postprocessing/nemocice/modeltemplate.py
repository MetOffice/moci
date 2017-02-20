#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2016 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    modeltemplate.py

DESCRIPTION
    Class definition for NEMO & CICE post processing - holds common
    properties and methods for NEMO and CICE models
'''

import abc
import os
import re

from collections import OrderedDict

import control
import nlist
import suite
import timer
import utils
import netcdf_utils
import netcdf_filenames

# Define constants
XX = 'General'
MM = '1m'
SS = '1s'
AA = '1y'
RR = 'Restarts'

MEANPERIODS = (MM, SS, AA)
MONTH_BASE = {
    # Number of files required to create a monthly mean file (360day calendar)
    '1m': -1, '15d': 2, '10d': 3, '5d': 6, '2d': 15, '1d': 30, '12h': 60
    }


class ModelTemplate(control.RunPostProc):
    '''
    Template class for input models
    '''
    __metatclass__ = abc.ABCMeta

    def __init__(self, input_nl='nemocicepp.nl'):
        name = self.__class__.__name__
        self.naml = getattr(nlist.loadNamelist(input_nl), name.lower())
        self.fields = self._fields
        if self.runpp:
            self.share = self._directory(self.naml.restart_directory,
                                         name.upper()[:-8] + ' SHARE')
            self.work = self._directory(self.naml.means_directory,
                                        name.upper()[:-8] + ' WORK')
            self.meansdir = os.path.join(self.share, 'archive_ready_means')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)
            self.suite.envars = utils.loadEnv('CYLC_SUITE_INITIAL_CYCLE_POINT',
                                              'INITCYCLE_OVERRIDE',
                                              append=self.suite.envars)

            # Initialise debug mode - calling base class method
            self._debug_mode(self.naml.debug)

    @property
    def runpp(self):
        '''
        Logical - Run postprocessing for given model
        Set via the [model]postproc namelist
        '''
        return self.naml.pp_run

    @property
    def methods(self):
        '''
        Returns a dictionary of methods available for this model to the
        main program
        '''
        return OrderedDict(
            [('archive_restarts', self.naml.archive_restarts),
             ('move_to_share',
              self.naml.create_means or self.naml.archive_means),
             ('create_means', self.naml.create_means),
             ('archive_means', self.naml.archive_means),
             ('archive_general',
              any(ftype[1] for ftype in self.archive_types if
                  isinstance(ftype[1], bool) and ftype[1])),
             ('finalise_debug', self.naml.debug)]
            )

    @property
    def _fields(self):
        ''' Returns a tuple of means fields available'''
        return ('',)

    @abc.abstractproperty
    def model_components(self):
        '''
        Returns a dictionary with keys comprising a list of model components.
        The component will be used as a prefix to any archived fieldsfiles
        including means.
        Overriding method in the calling model is required.
        '''
        msg = 'Model specific model_components property not implemented.\n\t'
        msg += 'return {component: [field1, field2]}'
        utils.log_msg(msg, level='WARN')
        raise NotImplementedError

    @abc.abstractproperty
    def model_realm(self):
        '''
        Returns a single lowercase character representing the data realm.
        Permitted realms are:
           a = atmosphere
           i = seaice
           l = land
           o = ocean
        Overriding method in the calling model is required.
        '''
        msg = 'Model specific model_realm propetry not implemented.\n\t'
        msg += 'return single lowercase char from permitted list: [a, i, l, o]'
        utils.log_msg(msg, level='WARN')
        raise NotImplementedError

    @property
    def rsttypes(self):
        ''' Returns a tuple of restart file types available '''
        return ('',)

    @property
    def archive_types(self):
        '''
        Additional namelist logicals controlling the archive of files
        other than restarts and means.
        Returns a list of tuples: (method_name, bool)
        '''
        return []

    @property
    def prefix(self):
        ''' Common filename prefix '''
        return self.suite.prefix

    @property
    def month_base(self):
        '''Base component used to create the monthly mean file'''
        return self.naml.base_component

    @abc.abstractproperty
    def set_stencil(self):
        '''
        Returns the dictionary of regular expressions for matching a set of
        restart files or means files.
        The calling argument for each netcdf_filenames method is an object of
        type netcdf_filenames.NCFilename.
        Overriding for RR is required in the calling model.
        '''
        return {
            RR: lambda x: 'NotImplementedError - Restarts Set Stencil',
            MM: lambda fn_vars: netcdf_filenames.month_set(fn_vars),
            SS: lambda fn_vars: netcdf_filenames.season_set(fn_vars),
            AA: lambda fn_vars: netcdf_filenames.year_set(fn_vars),
            }

    @property
    def end_stencil(self):
        '''
        Returns the dictionary of regular expressions for matching files at the
        end of a month, season or year.
        The calling argument for each netcdf_filenames method is an object of
        type netcdf_filenames.NCFilename.
        '''
        return {
            MM: lambda fn_vars: netcdf_filenames.month_end(fn_vars),
            SS: lambda fn_vars: netcdf_filenames.season_end(fn_vars),
            AA: lambda fn_vars: netcdf_filenames.year_end(fn_vars),
            }

    @abc.abstractproperty
    def mean_stencil(self):
        '''
        Returns the dictionary of regular expressions for matching means files
        available.
        The calling argument for each netcdf_filenames method is an object of
        type netcdf_filenames.NCFilename.
        Overriding of XX is required in the calling model.
        '''
        mean_stencil = {XX: lambda x: 'NotImplemented - General Mean Template'}
        for period in ['All'] + list(MEANPERIODS):
            mean_stencil[period] = lambda fn_vars: \
                netcdf_filenames.mean_stencil(fn_vars)
        return mean_stencil

    @property
    def additional_means(self):
        '''
        Returns a list of means to be archived; additional to the standard
        monthly, seasonal and annual means files
        '''
        means = self.naml.means_to_archive if self.naml.means_to_archive else []
        if not isinstance(means, list):
            means = [means]
        return means

    @property
    def rebuild_cmd(self):
        '''
        Command: Executable + Arguments upto but not including
        the filename(s)
        '''
        try:
            return self.naml.exec_rebuild
        except AttributeError:
            # Not all models require rebuilding
            pass

    @property
    def rebuild_suffix(self):
        '''
        Returns dictionary with two keys, profiding the suffix for components
        to rebuild:
            REGEX - REGular EXpression representing all PEs
            ZERO  - String representing PE0
        '''
        return {'REGEX': '', 'ZERO': ''}

    @timer.run_timer
    def get_raw_output(self, source):
        '''
        Create a list of means files available with the raw model output
        filenames.
        Arguments:
            source = source directory
        '''
        raw_files = []
        for field in self.fields:
            raw_files += utils.get_subset(source, self.mean_stencil[XX](field))

        return raw_files

    @timer.run_timer
    def move_to_share(self, pattern=None):
        '''
        Move unprocessed means files to SHARE
        Optional arguments:
            pattern = regex to match filenames.  Default=Standard means
        '''
        if pattern:
            workfiles = utils.get_subset(self.work, pattern)
        else:
            # Default pattern - all means files
            workfiles = self.get_raw_output(self.work)

        if workfiles and self.work != self.share:
            utils.log_msg('Moving files to SHARE directory')
            utils.move_files(workfiles, self.share, originpath=self.work)

        if not pattern:
            # enforce netCDF filename convention for standard means
            for fname in self.get_raw_output(self.share):
                ncfile = self.filename_components(fname)
                ncfile.rename_ncf(os.path.join(self.share, fname))
            self.fields = tuple([f.replace('_', '-') for f in self.fields])

    def timestamps(self, month, day, process='archive'):
        '''
        Returns True/False - Match a file to given timestamps to establish
        need for processing (rebuild or archive)
        '''
        nlvar = getattr(self.naml, process + '_timestamps')
        if not isinstance(nlvar, list):
            nlvar = [nlvar]
        return bool([ts for ts in nlvar if [month, day] == ts.split('-')] or
                    not nlvar)

    @staticmethod
    def get_date(filename, enddate=False):
        '''
        Returns a tuple representing the date extracted from a filename.
        Overriding method in the calling model is required.
        By default the date returned is the first (start) date in the filename.
        '''
        return netcdf_filenames.ncf_getdate(filename, enddate=enddate)

    def periodset(self, inputs, datadir=None, archive=False):
        '''
        Returns the files available to create a given set:
           RR = all restart files
           MM/SS/AA = All files belonging to a given month, season or year.
        If archiving:
           Period index is incremented to return the pattern for files
           belonging to a period rather than the pattern for filenames for
           creating a period .
        '''
        if not datadir:
            datadir = self.share
        try:
            period = MEANPERIODS[MEANPERIODS.index(inputs.base)+1] if \
                archive else inputs.base
            tempbase = inputs.base
            if period == MM:
                inputs.base = self.month_base
            pattern = self.set_stencil[period](inputs)
            inputs.base = tempbase
        except AttributeError:
            # Restart Files - `inputs` is a simple string
            pattern = self.set_stencil[RR](inputs)
        except IndexError:
            # Archive all annual means - MEANPERIODS list range is exceeded
            inputs.start_date = (r'\d{4}', r'\d{2}', r'\d{2}')
            pattern = self.mean_stencil[inputs.base](inputs)

        return utils.get_subset(datadir, pattern)

    def periodend(self, inputs, datadir=None, archive=False):
        '''
        Returns the files available belonging to the end of a given period:
           MM/SS/AA = Files available which represent the 3rd (4th for annual)
           file of a given month, season or year.
        If archiving:
           Period index is incremented to return the pattern for files
           belonging to a period rather than the pattern for filenames for
           creating a period
        '''
        if not datadir:
            datadir = self.share

        try:
            period = MEANPERIODS[MEANPERIODS.index(inputs.base)+1] if \
                archive else inputs.base
            tempbase = inputs.base
            if period == MM:
                inputs.base = self.month_base
            pattern = self.end_stencil[period](inputs)
            inputs.base = tempbase
            return utils.get_subset(datadir, pattern)
        except IndexError:
            # Archive annual means - MEANPERIODS list range is exceeded
            return [None, ]

    def filename_components(self, filename):
        '''
        Initialise a netCDF filename object based on a filename produced
        as direct output from the model.
        '''
        for model in self.model_components:
            field = self.model_components[model]
            if field:
                match = [f for f in self.model_components[model] if
                         f in filename]
                if match:
                    field = match[0].replace('_', '-')
                    component = model
                    break
            else:
                component = model

        if self.rebuild_suffix['REGEX']:
            # Add processor number (if available) to field
            patt = r'.*{}.*({})'.format(match[0], self.rebuild_suffix['REGEX'])
            try:
                field += re.match(patt, filename).group(1).rstrip('.nc')
            except AttributeError:
                # No processor number
                pass

        base = re.split(r'[._\-]', filename)[1]
        startdate = self.get_date(filename)

        try:
            ncf = netcdf_filenames.NCFilename(
                component, self.prefix, self.model_realm,
                base=base, start_date=startdate, custom=field
                )
        except NameError as exc:
            msg = 'unable to extract "{}" from filename: {}'.\
                format(str(exc.message).split('\'')[1], filename)
            utils.log_msg('filename_components: ' + msg, level='ERROR')
            ncf = netcdf_filenames.NCFilename('component', 'PREFIX', 'R')

        return ncf

    def loop_inputs(self, fields):
        '''
        Generator function for looping over:
          * Fields (`list` argument)
          * Periods (years, seasons, months)
        '''
        for cmpt in self.model_components:
            inputs = netcdf_filenames.NCFilename(cmpt, self.prefix,
                                                 self.model_realm)
            for field in fields:
                inputs.custom = '_' + field if field else ''
                # Loop over MM, SS, AA periods
                for period in MEANPERIODS:
                    inputs.base = period
                    yield inputs

    # *** REBUILD *** #########################################################
    def rebuild_restarts(self):
        '''
        Method for rebuilding restart files - if required it is overridden
        in the calling model
        '''
        pass

    # *** MEANING *** #########################################################
    @property
    def means_cmd(self):
        '''
        Command: Executable + Arguments upto but not including
        the filename(s)
        '''
        try:
            return self.naml.means_cmd
        except AttributeError:
            raise UserWarning('[FAIL] MEANS executable not defined for model.')

    @staticmethod
    def describe_mean(inp):
        '''Compose informative description for mean under consideration'''
        target = inp.base
        if target == MM:
            months = [None, 'January', 'February', 'March', 'April',
                      'May', 'June', 'July', 'August', 'September',
                      'October', 'November', 'December']
            period = 'Monthly'
            subperiod = months[int(inp.start_date[1])]

        elif target == SS:
            # Keywords for the seasons dictionary are used in the output
            # message, prior to the year, to describe the mean being processed
            seasons = {'Winter, ending': [12, 1, 2],
                       'Spring': [3, 4, 5],
                       'Summer': [6, 7, 8],
                       'Autumn': [9, 10, 11]}
            period = 'Seasonal'
            subperiod = [s for s in seasons if
                         int(inp.start_date[1]) in seasons[s]][0]

        elif target == AA:
            period = 'Annual'
            subperiod = 'year ending December'
            target = '0y'

        else:
            utils.log_msg('describe_mean - Unknown mean period:' + target,
                          level='ERROR')
            period = 'Unknown'
            subperiod = ''

        meandate = ' '.join([subperiod, inp.calc_enddate(target=target)[0]])
        meantype = ' '.join([inp.custom.strip('_'), period])
        return '{} mean for {}'.format(meantype, meandate)

    @timer.run_timer
    def create_means(self):
        '''
        Create monthly, seasonal, annual means.
        Delete component files as necessary.
        '''
        utils.create_dir(self.meansdir)

        for inputs in self.loop_inputs(self.fields):
            # Loop over set of means which it should be possible to create
            # from files available.
            for setend in self.periodend(inputs):
                period = inputs.base
                inputs.start_date = self.get_date(setend)
                describe = self.describe_mean(inputs)
                meanset = self.periodset(inputs)
                lenset = {
                    # Number of component files required for each mean
                    MM: MONTH_BASE[self.month_base],
                    SS: 3,
                    AA: 4
                    }

                if len(meanset) == lenset[period]:
                    # Reset start date to beginning of the meaning period:
                    inputs.start_date = self.get_date(sorted(meanset)[0])
                    meanfile = self.mean_stencil[period](inputs)

                    fn_full = os.path.join(self.share, meanfile)
                    if os.path.isfile(fn_full):
                        # Mean file may already exist from a previous attempt
                        msg = '{} already exists: {}'.format(describe, meanfile)
                        utils.log_msg(msg, level='INFO')
                        icode = 0
                    else:
                        cmd = '{} {} {}'.format(self.means_cmd,
                                                (' ').join(meanset),
                                                meanfile)
                        icode, output = utils.exec_subproc(cmd, cwd=self.share)

                    if icode == 0 and os.path.isfile(fn_full):
                        msg = 'Created {}: {}'.format(describe, meanfile)
                        utils.log_msg(msg, level='OK')

                        # Meaning gets the time_bounds variables wrong
                        # so correct them here
                        self.fix_mean_time(utils.add_path(meanset, self.share),
                                           fn_full)

                        if period == MM and \
                                self.month_base not in self.additional_means:
                            msg = 'Deleting component means for '
                            utils.log_msg(msg + meanfile)
                            utils.remove_files(meanset, path=self.share)
                        else:
                            # Move component files to `archive_ready` directory
                            utils.move_files(meanset, self.meansdir,
                                             originpath=self.share)

                    else:
                        msg = '{C}: Error={E}\n{O}\nFailed to create {M}: {L}'
                        msg = msg.format(C=self.means_cmd, E=icode, O=output,
                                         M=describe, L=meanfile)
                        utils.log_msg(msg, level='FAIL')

                elif lenset[period] == -1:
                    # Base component of one month - no monthly mean to create
                    msg = 'create_means: Monthly means output directly by model'
                    utils.log_msg(msg, level='INFO')

                else:
                    # Insuffient component files available to create mean.
                    msg = '{} not possible as only got {} file(s): \n\t{}'.\
                        format(describe, len(meanset), ', '.join(meanset))
                    if self.means_spinup(describe, inputs.start_date):
                        # Model in spinup period for the given mean.
                        # Insufficent component files is expected.
                        msg = msg + '\n\t -> Means creation in spinup mode.'
                        utils.log_msg(msg, level='INFO')
                    else:
                        # This error should fail, even in debug mode, otherwise
                        # components will be archived and deleted.
                        utils.log_msg(msg, level='FAIL')

    def means_spinup(self, description, meandate):
        '''
        A mean cannot be created if the date of the mean is too close the the
        model start time (in the spinup period) to allow all required
        components to be available.
        The mean date is year/month taken from the end of the meaning period.
        Returns True if the model is in the spinup period for creation of
        a given mean.
        '''
        try:
            # An override is required for Single Cycle test suites
            initialcycle = self.suite.envars.INITCYCLE_OVERRIDE
        except AttributeError:
            initialcycle = self.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT
        second_year = str(int(meandate[0]) - 1) == initialcycle[0:4]
        if meandate[0] == initialcycle[0:4]:
            if 'Monthly' in description:
                # Spinup during the first model month if initialised
                # after the first day of a month.
                spinup = int(initialcycle[4:6]) == int(meandate[1]) and \
                    initialcycle[6:8] != '01'
            elif 'Seasonal' in description:
                # Spinup during the first model season if initialised
                # after the first month of a season.
                mths = [meandate[1],
                        str(int(meandate[1]) - 1).zfill(2)]
                if initialcycle[6:8] != '01':
                    mths.append(str(int(meandate[1]) - 2).zfill(2))
                spinup = initialcycle[4:6] in mths
            elif 'Annual' in description:
                spinup = True
            else:
                msg = 'means_spinup: unknown meantype requested.\n'
                msg += '\tUnable to assess whether model is in spin up mode.'
                utils.log_msg(msg, level='WARN')
                spinup = False
        elif second_year and initialcycle[4:6] == '12' and \
                initialcycle[6:8] != '01':
            spinup = ('Annual' in description) or \
                ('Seasonal' in description and meandate[1] == '02')
        else:
            spinup = False

        return spinup

    # *** ARCHIVING *** #######################################################
    @property
    def buffer_archive(self):
        '''
        Number of unprocessed files to retain after archiving
        task is complete
        '''
        if self.suite.finalcycle or not self.naml.buffer_archive:
            buffer_arch = 0
        else:
            buffer_arch = self.naml.buffer_archive

        return buffer_arch

    def component(self, field):
        '''
        Returns the model component assigned to the field provided'''
        component = None
        for model in self.model_components:
            if field:
                assigned = self.model_components[model]
                assigned += [f.replace('_', '-') for f in assigned]
                if field in assigned:
                    component = model
            else:
                component = model
        return component

    @timer.run_timer
    def archive_means(self):
        '''
        Compile list of means files to archive.
        Only delete if all files are successfully archived.
        '''
        to_archive = []
        do_not_delete = []
        for inputs in self.loop_inputs(self.fields):
            for setend in self.periodend(inputs, archive=True):
                inputs.start_date = self.get_date(setend) if setend else \
                    (r'\d{4}', r'\d{2}', r'\d{2}')
                # Sort list so periodend file is the last of the set to be
                # processed - necessary to pick up all available sets in retry
                # following failure during archiving
                for mean in sorted(self.periodset(inputs, archive=True)):
                    to_archive.append(mean)

        for field in self.fields:
            custom = '_' + field if field else ''
            ncf = netcdf_filenames.NCFilename(self.component(field),
                                              self.suite.prefix,
                                              self.model_realm,
                                              custom=custom)

            # Select all files in "archive ready" directory
            if os.path.exists(self.meansdir):
                pattern = r'{}.*{}\.nc$'.format(self.prefix.lower(), field)
                files = utils.get_subset(self.meansdir, pattern)
                to_archive += [os.path.join(self.meansdir, fn) for fn in files]

            # Select additional means files, not in month_base or standard means
            for other_mean in self.additional_means:
                if other_mean not in [self.month_base] + list(MEANPERIODS):
                    ncf.base = other_mean
                    pattern = self.mean_stencil['All'](ncf)
                    for mean in utils.get_subset(self.share, pattern):
                        to_archive.append(mean)

            # Final cycle only - select all standard means remaining in share
            if self.suite.finalcycle:
                # Archive, but do not delete means
                for period in MEANPERIODS:
                    ncf.base = period
                    pattern = self.mean_stencil['All'](ncf)
                    for mean in utils.get_subset(self.share, pattern):
                        do_not_delete.append(mean)

        to_archive += do_not_delete

        # Debugmode - removed already archived files from the list
        to_archive = [fn for fn in to_archive if not fn.endswith('ARCHIVED')]
        if to_archive:
            for fname in to_archive:
                # Compress means files prior to archive.
                if (self.naml.compression_level > 0 and
                        '_diaptr' not in fname and '_scalar' not in fname):
                    # NEMO diaptr files cannot currently be compressed.
                    rcode = self.compress_file(fname, self.naml.compress_means)
                    if rcode != 0:
                        # Do not archive - failed to compress (debug_mode only)
                        continue

                arch_rtn = self.archive_files(fname)[fname]
                if arch_rtn != 'FAILED' and fname not in do_not_delete:
                    # Delete successfully archived files except those to remain
                    # after the final cycle
                    utils.log_msg('Deleting archived file: ' + fname)
                    dirname = os.path.dirname(fname)
                    if utils.get_debugmode():
                        # Append "ARCHIVED" suffix to file rather than delete
                        if not dirname:
                            fname = os.path.join(self.share, fname)
                        os.rename(fname, fname + '_ARCHIVED')
                    else:
                        utils.remove_files(
                            fname,
                            path=dirname if dirname else self.share
                            )
        else:
            utils.log_msg(' -> Nothing to archive')

    @timer.run_timer
    def archive_restarts(self):
        '''
        Compile list of restart files to archive and subsequently deletes them.
        Rebuild files as necessary on a model by model basis.
        '''
        # Rebuild restart files as required
        self.rebuild_restarts()

        for rsttype in self.rsttypes:
            final_rst = None
            rstfiles = self.periodset(rsttype)
            rstfiles = sorted(rstfiles)
            to_archive = []
            while len(rstfiles) > self.buffer_archive:
                rst = rstfiles.pop(0)
                if self.suite.finalcycle and len(rstfiles) == 0:
                    final_rst = rst
                month, day = self.get_date(rst)[1:3]
                if self.timestamps(month, day) or final_rst:
                    to_archive.append(rst)
                else:
                    msg = 'Only archiving periodic restarts: ' + \
                        str(self.naml.archive_timestamps)
                    msg += '\n -> Deleting file:\n\t' + str(rst)
                    utils.log_msg(msg)
                    utils.remove_files(rst, path=self.share)

            if to_archive:
                arch = self.archive_files(to_archive)
                to_delete = [fn for fn in arch if arch[fn] == 'SUCCESS']
                try:
                    # Do not delete the final restart file following archive
                    to_delete.remove(final_rst)
                except ValueError:
                    pass
                msg = 'Deleting archived files: \n\t' + '\n\t'.join(to_delete)
                if utils.get_debugmode():
                    # Append "ARCHIVED" suffix to files, rather than deleting
                    for fname in to_delete:
                        fname = os.path.join(self.share, fname)
                        os.rename(fname,
                                  fname.rstrip('_ARCHIVED') + '_ARCHIVED')
                else:
                    utils.remove_files(to_delete, path=self.share)
            else:
                msg = ' -> Nothing to archive'
                if rstfiles:
                    msg = '{} - {} restart{} files available ({} retained).'.\
                        format(msg, len(rstfiles), rsttype,
                               self.buffer_archive)
            utils.log_msg(msg)

    @timer.run_timer
    def archive_general(self):
        '''Call archive methods for additional model file types'''
        for method, archive in self.archive_types:
            if archive:
                try:
                    getattr(self, 'archive_' + method)()
                except AttributeError:
                    msg = 'Archive method not implemented: archive_' + method
                    utils.log_msg('archive_general: ' + msg, level='FAIL')

    @timer.run_timer
    def archive_files(self, filenames):
        '''
        Archive a one or more files.
        Returns a dictionary of requested files reporting success or failure.
        '''
        returnfiles = {}
        if not isinstance(filenames, list):
            filenames = [filenames]

        for fname in filenames:
            rcode = self.suite.archive_file(fname)
            if rcode == 0:
                utils.log_msg('Archive successful.', level='OK')
                returnfiles[fname] = 'SUCCESS'
            else:
                msg = 'Failed to archive file: {}. Will try again later.'.\
                    format(fname)
                returnfiles[fname] = 'FAILED'
                utils.log_msg(msg, level='WARN')

        return returnfiles

    @timer.run_timer
    def compress_file(self, fname, utility):
        '''Create command to compress netCDF file'''
        if utility == 'nccopy':
            rcode = self.suite.preprocess_file(
                utility,
                os.path.join(self.share, fname),
                compression=self.naml.compression_level,
                chunking=self.naml.chunking_arguments
                )
        else:
            utils.log_msg('Preprocessing command not yet implemented',
                          level='ERROR')
            rcode = 99
        return rcode

    def fix_mean_time(self, infiles, meanfile):
        '''
        Call fix_times to ensure that time and time_bounds in meanfile
        are correct
        '''
        if self.naml.correct_time_variables or \
                self.naml.correct_time_bounds_variables:
            time_vars = self.naml.time_vars
            if not isinstance(time_vars, (list, tuple)):
                time_vars = [time_vars]

            msg = 'fix_mean_time - Correcting mean time in file: '
            utils.log_msg(msg + meanfile, level='INFO')
            file_log = ''
            for var in time_vars:
                ret_msg = netcdf_utils.fix_times(
                    infiles, meanfile, var,
                    do_time=self.naml.correct_time_variables,
                    do_bounds=self.naml.correct_time_bounds_variables)
                file_log = file_log + ret_msg
            if file_log:
                utils.log_msg(ret_msg, level='OK')
