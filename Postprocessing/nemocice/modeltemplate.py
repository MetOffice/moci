#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

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
import copy

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
DD = '1x'
RR = 'Restarts'

MEANPERIODS = (MM, SS, AA)


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
            self.meansets = self._mean_bases()
            self.requested_means = [m for m in MEANPERIODS
                                    if self.meansets[m][0]]
            msg = 'Processing {} means'.format(','.join(self.requested_means))
            utils.log_msg(msg, level='INFO')

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
             ('move_to_share', any([self.naml.create_monthly_mean,
                                    self.naml.create_seasonal_mean,
                                    self.naml.create_annual_mean,
                                    self.naml.create_decadal_mean,
                                    self.naml.archive_means])),
             ('create_means', any([self.naml.create_monthly_mean,
                                   self.naml.create_seasonal_mean,
                                   self.naml.create_annual_mean,
                                   self.naml.create_decadal_mean])),
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
    def cfcompliant_output(self):
        ''' Return "True" if the raw model output datestamp is CF-compliant '''
        return True

    @property
    def base_component(self):
        '''Base component used to create the first mean file'''
        return self.naml.base_component

    def _mean_bases(self):
        '''
        Return a dictionary of base periods for each mean:
           { <PERIOD>: tuple(<PERIOD BASE>, <SET LENGTH> }
             <PERIOD>      = MM,SS,AA,DD
             <PERIOD BASE> = Base component used to create the mean
             <SET LENGTH>  = Number of base component files to create the mean
        '''
        basecmpt = self.naml.base_component
        multiplier = float(basecmpt[:-1])

        if os.environ['CYLC_CYCLING_MODE'] in ['360day', 'integer']:
            cal_hd = 'hd'
        else:
            cal_hd = ''

        all_periods = {
            '1m': [None, 1 if (basecmpt == '1m') else
                   (30 if (basecmpt[-1] == 'd' and cal_hd) else
                    (720 if (basecmpt[-1] == 'h' and cal_hd) else 0))],
            '1s': [None, 1 if (basecmpt == '1s') else
                   (3 if (basecmpt[-1] in cal_hd + 'm') else 0)],
            '1y': [None, 1 if (basecmpt == '1y') else
                   (4 if (basecmpt[-1] in cal_hd + 'ms') else 0)],
            '1x': [None, 1 if (basecmpt == '10y') else
                   (10 if (basecmpt[-1] in cal_hd + 'msy') else 0)],
            }

        base_mean = None
        for i, period in enumerate(MEANPERIODS):
            if all_periods[period][1] == 0:
                # This period mean has already been assessed as not possible
                continue

            try:
                nextp = MEANPERIODS[i + 1]
                all_periods[nextp][0] = period
            except IndexError:
                # No further means possible
                nextp = None

            if base_mean:
                all_periods[period][0] = basecmpt
            else:
                if all_periods[period][1] % multiplier == 0 and \
                        all_periods[period][1] >= multiplier:
                    all_periods[period] = [
                        basecmpt, int(all_periods[period][1] / multiplier)
                        ]
                    base_mean = period
                else:
                    # mean is not possible on the given base
                    if nextp:
                        all_periods[nextp][0] = basecmpt
                        all_periods[nextp][1] *= \
                            all_periods[period][1]
                    all_periods[period] = [None, 0]
                    continue

            meantitles = {'1m': 'monthly',
                          '1s': 'seasonal',
                          '1y': 'annual',
                          '1x': 'decadal'}
            if getattr(self.naml, 'create_{}_mean'.format(meantitles[period])):
                # Update the base component for the next mean
                basecmpt = period
            else:
                if nextp:
                    all_periods[nextp][0] = period
                    all_periods[nextp][1] *= all_periods[period][1]
                all_periods[period] = [None, 0]

        return all_periods

    def set_stencil(self, period, fn_vars):
        '''
        Return the regular expression for matching a set of files
        for a given period.

        Restart Files (period==RR):
           The regex should match ALL restart files of the given type (fn_vars)
          irrespective of date stamp

        Means Files (period in [MM,SS,AA,XX]):
           The regex should match the set of component files for a period mean
          with the given start date (fn_vars.start_date) and base component
          (fn_vars.base)

        Arguments:
            period  - <type str> - One of MEANPERIODS
            fn_vars - Type depends on the file type in question -
                         Restart files: <type tuple> - One of self.rsttypes
                         Means files:   <type netcdf_filename.NCFilename>
        '''
        if period == RR:
            set_stencil = self.rst_set_stencil(fn_vars)
        else:
            set_stencil = netcdf_filenames.period_set(period, fn_vars)
        return set_stencil

    def end_stencil(self, period, fn_vars):
        '''
        Return the regular expression for matching files at the end
        of a given period (monthly, seasonal, annual), irrespective
        of month, season, year etc.
        Date stamps will be calculated based on the mean reference date
        and the base component of the period mean (fn_vars.base)

        The presence of the "end" file indicates that a mean can be
        created/archived as sufficient components must logically exist.

        Arguments:
            period  - <type str> - One of MEANPERIODS
            fn_vars - <type netcdf_filename.NCFilename>
        '''
        return netcdf_filenames.period_end(period, fn_vars, self.suite.meanref)

    def mean_stencil(self, fn_vars, base=None):
        r'''
        Arguments:
            fn_vars - The type of this argment will determine the return value
                      of the method:

               <type netcdf_filename.NCFilename> -
                   For filenames in accordance with the Met Office filenaming
                   convention for netCDF diagnostic data.
.
                   Return a mean filename string with date stamp based on
                   fn_vars.base and fn_vars.start_date
                   Where fn_vars.start_date==('\d{4}',)*3 the return value
                   becomes a regular expression to match any file with a
                   <frequency> facet matching the string: fn_vars.base

               <type str> -
                   Return a regular expression to match raw model
                   output filenames containing the string: fn_vars

        Optional arguments:
            base    - Valid only for the general_mean_stencil:
                         <type str> - Matches files with base component=fn_vars
                         Default=<type NoneType> - Matches files with any
                                      standard base component

        '''
        if isinstance(fn_vars, netcdf_filenames.NCFilename):
            mean_stencil = netcdf_filenames.mean_stencil(fn_vars)
        else:
            # General regular expression for raw model output
            mean_stencil = self.general_mean_stencil(fn_vars, base=base)
        return mean_stencil

    @abc.abstractmethod
    def rst_set_stencil(self, rsttype):
        '''
        Return a regular expression to match restart filenames output
        directly by the model.
        '''
        msg = 'Restart file regular expression not available.'
        utils.log_msg(msg, level='WARN')
        raise NotImplementedError

    @abc.abstractmethod
    def general_mean_stencil(self, field, base=None):
        '''
        Return a regular expression to match means filenames output
        directly by the model.
        '''
        msg = 'Means file regular expression for model output not available.'
        utils.log_msg(msg, level='WARN')
        raise NotImplementedError

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
            raw_files += utils.get_subset(source, self.mean_stencil(field))

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
                ncfile.rename_ncf(os.path.join(self.share, fname),
                                  target=self.datestamp_period(fname))
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

    def get_date(self, filename, enddate=False):
        '''
        Returns a tuple representing the date extracted from a filename.
        Overriding method in the calling model is required.
        By default the date returned is the first (start) date in the filename.
        Arguments:
           filename - <type str>
        Optional arugments:
           enddate  - <type bool> Return the end date from the datestamp
        '''
        rtndate = list(netcdf_filenames.ncf_getdate(filename, enddate=enddate))
        if len(rtndate) == 2:
            rtndate.append('01')
            if enddate and not self.cfcompliant_output:
                rtndate[2] = self.suite.monthlength(rtndate[1])
        return tuple(rtndate)


    def periodfiles(self, inputs, call_method,
                    datadir=None, archive_mean=False):
        '''
        Returns the files available to create a given set:
           RR = all restart files
           MM/SS/AA = All files belonging to a given month, season or year.

        Arguments:
           inputs       - <type NCFilename> for means files
                          <type tuple> for restart files
           call_method  - <type str> One of ['set', 'end', 'mean']
                          "set" calls self.set_stencil to return regex for the
                        period set
                          "end" calls self.end_stencil to return regex for the
                        end of period file
                          "mean" calls self.mean_stencil to return a general
                        regex for the mean
        Optional Arguments:
           datadir      - Path to directory containing component files
                          Default=self.share
           archive_mean - Should be true when called from self.archive_means.
                          Period index is incremented to return the pattern for
                        files belonging to a period rather than the pattern for
                        filenames for creating a period.
        '''
        if not datadir:
            datadir = self.share

        tmp_inputs = copy.copy(inputs)
        if archive_mean:
            if inputs.base == self.requested_means[-1]:
                # Archive all top mean files
                call_method = ''
                period = inputs.base
                tmp_inputs.start_date = (r'\d{4}', r'\d{2}', r'\d{2}')
            else:
                period = self.requested_means[self.requested_means.
                                              index(inputs.base)+1]
        else:
            try:
                # Create means
                period = inputs.base
                tmp_inputs.base = self.meansets[period][0]
            except AttributeError:
                # Restart Files
                # "inputs" is <type tuple> with no "base" attribute
                period = RR

        try:
            pattern = getattr(self,
                              call_method + '_stencil')(period, tmp_inputs)
        except AttributeError:
            # Archive according to a general mean stencil - period not required
            pattern = self.mean_stencil(tmp_inputs) + '$'

        return utils.get_subset(datadir, pattern)

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

        for elem in re.split(r'[._\-]', filename):
            if re.match(r'\d+[hdmsyxHDMSYX]', elem):
                base = elem
                break
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

    def datestamp_period(self, fname):
        '''
        Return period of data contained in a file according to the
        filename datestamp.
        '''
        date = [int(x) for x in self.get_date(fname)]
        enddate = [int(x) for x in self.get_date(fname, enddate=True)]

        try:
            namebase = re.match(r'.*[_.](\d+[hdm])', fname).group(1)
        except IndexError:
            utils.log_msg('file_date_period - Invalid filename:' + fname,
                          level='ERROR')
            # Set default value for debug mode
            namebase = '1d'

        frequency, base = utils.get_frequency(namebase)
        delta = utils.get_frequency(namebase, rtn_delta=True)
        multiplier = 0 if self.cfcompliant_output else frequency
        data_period = None
        while not data_period:
            multiplier += frequency
            date = utils.add_period_to_date(date, delta)

            if date[:len(enddate)] == enddate:
                data_period = str(multiplier) + base
            elif date[:len(enddate)] > enddate:
                data_period = str(multiplier - frequency) + base

        if data_period == '30d' and \
                any([self.suite.envars.CYLC_CYCLING_MODE == '360day',
                     self.suite.envars.CYLC_CYCLING_MODE == 'integer']):
            data_period = '1m'
        elif data_period == '24h':
            data_period = '1d'

        return data_period

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
                for mean in MEANPERIODS:
                    inputs.base = mean
                    if mean in self.requested_means:
                        # Yield NCFilename object for required mean periods
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

    def describe_mean(self, inp):
        '''Compose informative description for mean under consideration'''
        months = [None, 'January', 'February', 'March', 'April',
                  'May', 'June', 'July', 'August', 'September',
                  'October', 'November', 'December']

        target = inp.base
        year_stamp = int(inp.start_date[0])
        if target == MM:
            period = 'Monthly'
            subperiod = months[int(inp.start_date[1])]

        elif target == SS:
            # Keywords for the seasons dictionary are used in the output
            # message, prior to the year, to describe the mean being processed
            seasons = {}
            tag = ''
            for ssn in netcdf_filenames.seasonend(self.suite.meanref):
                ssn_mths = [int(ssn[0:2])]
                while len(ssn_mths) < 3:
                    next_mth = ssn_mths[len(ssn_mths) - 1] + 1
                    if next_mth == 13:
                        next_mth = 1
                        tag = ', ending'
                    ssn_mths.append(next_mth)

                name = '{}-{}-{}'.format(*[months[m][0:3] for m in ssn_mths])
                seasons[name + tag] = ssn_mths

            period = 'Seasonal'
            subperiod = [s for s in seasons if
                         int(inp.start_date[1]) in seasons[s]][0]
            if int(inp.start_date[1]) > 10:
                year_stamp += 1

        elif target == AA:
            period = 'Annual'
            subperiod = 'year ending ' + months[self.suite.meanref[1]]
            year_stamp += 1

        else:
            utils.log_msg('describe_mean - Unknown mean period:' + target,
                          level='ERROR')
            period = 'Unknown'
            subperiod = ''
            year_stamp = 0

        meandate = ' '.join([subperiod, str(year_stamp)])
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
            for setend in self.periodfiles(inputs, 'end'):
                period = inputs.base
                inputs.start_date = self.get_date(setend)
                describe = self.describe_mean(inputs)
                meanset = self.periodfiles(inputs, 'set')

                # Reset start date to beginning of the meaning period:
                inputs.start_date = self.get_date(sorted(meanset)[0])
                meanfile = self.mean_stencil(inputs)
                tidy_components = False
                if len(meanset) == self.meansets[period][1]:
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
                        tidy_components = True

                    else:
                        msg = '{C}: Error={E}\n{O}\nFailed to create {M}: {L}'
                        msg = msg.format(C=self.means_cmd, E=icode, O=output,
                                         M=describe, L=meanfile)
                        utils.log_msg(msg, level='FAIL')

                elif self.meansets[period][1] <= 1:
                    # Base component is equal to the period mean
                    msg = 'create_means: {} mean output directly by the model.'
                    utils.log_msg(msg.format(period), level='INFO')

                else:
                    # Insuffient component files available to create mean.
                    msg = '{} not possible as only got {} file(s): \n\t{}'.\
                        format(describe, len(meanset), ', '.join(meanset))
                    enddate = self.get_date(setend, enddate=True)
                    if self.means_spinup(describe, enddate):
                        # Model in spinup period for the given mean.
                        # Insufficent component files is expected.
                        msg = msg + '\n\t -> Means creation in spinup mode.'
                        utils.log_msg(msg, level='INFO')
                        tidy_components = True
                    else:
                        # This error should fail, even in debug mode, otherwise
                        # components will be archived and deleted.
                        utils.log_msg(msg, level='FAIL')

                if tidy_components:
                    # Either archive or delete base mean components as required
                    if period == self.requested_means[0] and \
                            self.base_component not in \
                            self.additional_means:
                        msg = 'Deleting component means for '
                        utils.log_msg(msg + meanfile)
                        utils.remove_files(meanset, path=self.share)
                    else:
                        # Move component files to `archive_ready` directory
                        utils.move_files(meanset, self.meansdir,
                                         originpath=self.share)

    def means_spinup(self, description, mean_enddate):
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
        initialcycle = [int(x) for x in
                        utils.cyclestring(specific_cycle=initialcycle)]

        enddate = list(mean_enddate)
        for datelist in enddate, initialcycle:
            while len(datelist) < 5:
                datelist.append(0)

        if 'Monthly' in description:
            delta = '-1m'
        elif 'Seasonal' in description:
            delta = '-1s'
        elif 'Annual' in description:
            delta = '-1y'
        elif 'Decadal' in description:
            delta = '-1x'
        else:
            msg = 'means_spinup: unknown meantype requested.\n'
            msg += '\tUnable to assess whether model is in spin up mode.'
            utils.log_msg(msg, level='WARN')
            delta = '0d'

        return initialcycle[:5] > utils.add_period_to_date(enddate, delta)[:5]


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
            for setend in self.periodfiles(inputs, 'end', archive_mean=True):
                inputs.start_date = self.get_date(setend)
                to_archive += self.periodfiles(inputs, 'set', archive_mean=True)

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

            # Select additional means files, not in base_component
            # or standard means
            for other_mean in self.additional_means:
                if other_mean not in [self.base_component] + \
                        self.requested_means:
                    ncf.base = other_mean
                    pattern = self.mean_stencil(ncf)
                    to_archive += utils.get_subset(self.share, pattern)

            # Final cycle only - select all required means remaining in share
            # as components of future higher means
            if self.suite.finalcycle:
                # Archive, but do not delete means except the top standard mean
                # which is already accounted for and should be deleted
                arch_cmpts = self.requested_means[:-1] + self.additional_means
                for period in arch_cmpts:
                    ncf.base = period
                    pattern = self.mean_stencil(ncf)
                    do_not_delete += utils.get_subset(self.share, pattern)

        to_archive += do_not_delete
        # Remove duplicates and sort list so period end files are dealt with
        # after the rest of the set.
        to_archive = sorted(list(set(to_archive)))

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
            rstfiles = self.periodfiles(rsttype, 'set')
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
