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
import shutil

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
        self.naml = utils.Variables()
        namelists_in_file = nlist.loadNamelist(input_nl)
        for nl_name in dir(namelists_in_file):
            modelprefix = name.lower().replace('postproc', '') + '_'
            if nl_name.startswith(modelprefix):
                setattr(self.naml, nl_name[len(modelprefix):],
                        getattr(namelists_in_file, nl_name))

        self.mean_fields = self._mean_fields
        self.inst_fields = self._inst_fields

        if self.runpp:
            self.share = self._directory(self.naml.pp.restart_directory,
                                         name.upper()[:-8] + ' SHARE')
            self.work = self._directory(self.naml.pp.work_directory,
                                        name.upper()[:-8] + ' WORK')
            self.diagsdir = os.path.join(self.share, 'archive_ready')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)

            # Initialise debug mode - calling base class method
            self._debug_mode(self.naml.pp.debug)
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
        return self.naml.pp.pp_run

    @property
    def methods(self):
        '''
        Returns a dictionary of methods available for this model to the
        main program
        '''
        process = self.suite.naml.process_toplevel is True
        archive = self.suite.naml.archive_toplevel is True
        return OrderedDict(
            [('move_to_share', (any([self.naml.processing.create_monthly_mean,
                                    self.naml.processing.create_seasonal_mean,
                                    self.naml.processing.create_annual_mean,
                                    self.naml.processing.create_decadal_mean])
                                and self.naml.processing.create_means) or
              self.naml.archiving.archive_means),

             ('create_general', process and
              any(ftype[1] for ftype in self.process_types if
                  ftype[1] is True)),

             ('create_means', process and self.naml.processing.create_means
              and any([self.naml.processing.create_monthly_mean,
                       self.naml.processing.create_seasonal_mean,
                       self.naml.processing.create_annual_mean,
                       self.naml.processing.create_decadal_mean])),

             ('prepare_archive', process and
              (self.naml.archiving.archive_restarts or
               self.naml.archiving.archive_means)),

             ('archive_restarts', archive and
              self.naml.archiving.archive_restarts),

             ('archive_general', archive and
              any(ftype[1] for ftype in self.process_types if
                  ftype[1] is True)),

             ('archive_means', archive and
              self.naml.archiving.archive_means),

             ('finalise_debug', self.naml.pp.debug)]
            )

    @property
    def _mean_fields(self):
        ''' Return a list of means fields available '''
        return ['',]

    @property
    def _inst_fields(self):
        ''' Return a list of instantaneous fields available '''
        return []

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
        msg = 'Model specific model_realm property not implemented.\n\t'
        msg += 'return single lowercase char from permitted list: [a, i, l, o]'
        utils.log_msg(msg, level='WARN')
        raise NotImplementedError

    @property
    def rsttypes(self):
        ''' Returns a tuple of restart file types available '''
        return ('',)

    @property
    def process_types(self):
        '''
        Return a list of tuples controlling the processing (creation/archive)
        of files other than restarts and means
           (<type str> method_name, <type bool>)
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
        return self.naml.processing.base_component

    def _mean_bases(self):
        '''
        Return a dictionary of base periods for each mean:
           { <PERIOD>: tuple(<PERIOD BASE>, <SET LENGTH> }
             <PERIOD>      = MM,SS,AA,DD
             <PERIOD BASE> = Base component used to create the mean
             <SET LENGTH>  = Number of base component files to create the mean
        '''
        basecmpt = self.base_component
        multiplier = float(basecmpt[:-1])

        if utils.calendar() == '360day':
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
            if getattr(self.naml.processing,
                       'create_{}_mean'.format(meantitles[period])):
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
        Return a list of means to be processed; additional to the standard
        monthly, seasonal and annual means files created by the app.
        '''
        return utils.ensure_list(self.naml.archiving.means_to_archive)

    @property
    def rebuild_cmd(self):
        '''
        Command: Executable + Arguments upto but not including
        the filename(s)
        '''
        try:
            return self.naml.processing.exec_rebuild
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
        Create a list of diagnostic files available with the raw model output
        filenames.
        Arguments:
            source = source directory
        '''
        raw_files = []
        for field in set(self.mean_fields + self.inst_fields):
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
            self.mean_fields = [f.replace('_', '-') for f in self.mean_fields]
            self.inst_fields = [f.replace('_', '-') for f in self.inst_fields]

    def timestamps(self, month, day, process='archive'):
        '''
        Returns True/False - Match a file to given timestamps to establish
        need for processing (rebuild or archive)
        '''
        namelist = 'archiving' if process == 'archive' else 'processing'
        nlvar = utils.ensure_list(getattr(getattr(self.naml, namelist),
                                          process + '_restart_timestamps'))
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

        if data_period == '24h':
            data_period = '1d'
        elif utils.calendar() == '360day':
            if data_period in ['30d', '720h', str(720 - 24 + frequency) + 'h']:
                # Non-CF will calculate (720h - 1d + frequency) for 1m period
                data_period = '1m'

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
            return self.naml.processing.means_cmd
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
        utils.create_dir(self.diagsdir)

        for inputs in self.loop_inputs(self.mean_fields):
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
                if len(meanset) == 1 and self.meansets[period][1] == 1:
                    # Base component is equal to the period mean
                    msg = 'create_means: {} mean output directly by the model.'
                    utils.log_msg(msg.format(period), level='INFO')

                elif len(meanset) == self.meansets[period][1]:
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
                        tidy_components = True
                    else:
                        msg = '{C}: Error={E}\n{O}\nFailed to create {M}: {L}'
                        msg = msg.format(C=self.means_cmd, E=icode, O=output,
                                         M=describe, L=meanfile)
                        utils.remove_files(fn_full, ignoreNonExist=True)
                        utils.log_msg(msg, level='FAIL')

                    # Meaning gets the time_bounds variables wrong
                    # so correct them here
                    self.fix_mean_time(utils.add_path(meanset, self.share),
                                       fn_full)
                    tidy_components = True

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
                        utils.move_files(meanset, self.diagsdir,
                                         originpath=self.share)

    @timer.run_timer
    def prepare_archive(self):
        '''
        Prepare files for archiving:
           * Rebuild restart files as required
           * Compress means files as required
        '''
        if self.naml.archiving.archive_restarts:
            # Rebuild restart files
            self.rebuild_restarts()

        if self.naml.archiving.archive_means:
            # Move means files ready for processing or archive
            # to "archive_ready" directory
            for inputs in self.loop_inputs(self.mean_fields):
                # Collect completed sets of mean components
                for setend in self.periodfiles(inputs, 'end',
                                               archive_mean=True):
                    inputs.start_date = self.get_date(setend)
                    fileset = self.periodfiles(inputs, 'set', archive_mean=True)
                    utils.move_files(fileset, self.diagsdir,
                                     originpath=self.share)

            match_fields = '({})'.format('|'.join(self.mean_fields))
            custom = '' if match_fields == '()' else '_' + match_fields
            ncf = netcdf_filenames.NCFilename('.*',
                                              self.prefix,
                                              self.model_realm,
                                              custom=custom)

            # Select additional means files, not in base_component
            # or standard means
            additional = set(self.additional_means).\
                difference(set(self.requested_means))
            if len(self.requested_means) > 0:
                additional = additional.difference(set([self.base_component]))

            if len(additional) > 0:
                match_bases = '({})'.format('|'.join(list(additional)))
                ncf.base = match_bases
                additional_means = utils.get_subset(self.share,
                                                    self.mean_stencil(ncf))
                utils.move_files(additional_means, self.diagsdir,
                                 originpath=self.share)

            if self.suite.finalcycle is True:
                # Final cycle only - select all required means remaining in
                # share directory as components of future higher means
                match_bases = '({})'.format('|'.join(list(additional) +
                                                     self.requested_means))
                ncf.base = match_bases
                final_means = utils.get_subset(self.share,
                                               self.mean_stencil(ncf))
                for fname in utils.add_path(final_means, self.share):
                    try:
                        shutil.copy2(fname, self.diagsdir)
                    except IOError:
                        msg = 'prepare_archive - Failed to copy {} to {}'
                        utils.log_msg(msg.format(fname, self.diagsdir),
                                      level='ERROR')

            if self.naml.processing.compression_level > 0:
                # Compress as required
                match_bases = '({})'.format('|'.join(list(additional) +
                                                     self.requested_means))
                for field in self.mean_fields:
                    if field.lower() in ['diaptr', 'scalar']:
                        # These NEMO files cannot currently be compressed.
                        pass
                    else:
                        self.compress_netcdf_files(match_bases, field)

    @timer.run_timer
    def compress_netcdf_files(self, base, fieldtype, sourcedir=None):
        '''
        Compress netCDF files matching given base period and custom facets
        Optional argument:
          sourcedir - Default=self.diagsdir
        '''

        source = sourcedir if sourcedir is not None else self.diagsdir
        fail_tag = '_COMPRESS_FAILED'

        custom = '_' + fieldtype if fieldtype else ''
        ncf = netcdf_filenames.NCFilename(self.component(fieldtype),
                                          self.prefix,
                                          self.model_realm,
                                          base=base,
                                          custom=custom)
        pattern = '{}({})?$'.format(self.mean_stencil(ncf), fail_tag)

        compress_files = utils.get_subset(source, pattern)
        for fname in utils.add_path(compress_files, source):
            if fname.endswith(fail_tag):
                # Previous debug mode error during compression - repeat
                os.rename(fname, fname[:-len(fail_tag)])
                fname = fname[:-len(fail_tag)]

            rcode = self.compress_file(
                fname,
                self.naml.processing.compress_netcdf,
                compression=self.naml.processing.compression_level,
                chunking=self.naml.processing.chunking_arguments
                )
            if rcode != 0:
                # Prevent archive - tag file as failed to compress (debug mode)
                os.rename(fname, fname + fail_tag)

    def means_spinup(self, description, mean_enddate):
        '''
        A mean cannot be created if the date of the mean is too close the the
        model start time (in the spinup period) to allow all required
        components to be available.
        The mean date is year/month taken from the end of the meaning period.
        Returns True if the model is in the spinup period for creation of
        a given mean.
        '''
        ptlen = len(self.suite.initpoint)
        enddate = list(mean_enddate)
        while len(enddate) < ptlen:
            enddate.append(0)

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

        return (self.suite.initpoint >
                utils.add_period_to_date(enddate, delta)[:ptlen])

    # *** ARCHIVING *** #######################################################
    @property
    def buffer_archive(self):
        '''
        Number of unprocessed files to retain after archiving
        task is complete
        '''
        if self.suite.finalcycle is True or \
                not self.naml.archiving.archive_restart_buffer:
            buffer_arch = 0
        else:
            buffer_arch = self.naml.archiving.archive_restart_buffer

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
    def create_general(self):
        ''' Call processing methods for additional model output filetypes '''
        for method, process in self.process_types:
            if process:
                try:
                    getattr(self, 'create_' + method)()
                except AttributeError:
                    # Not all filetypes to be archived require pre-processing
                    pass

    @timer.run_timer
    def archive_means(self):
        '''
        Archive files contained in the "archive ready" directory.
        Only delete if files are successfully archived.
        '''
        to_archive = []

        if os.path.exists(self.diagsdir):
            for field in self.mean_fields:
                # Pattern ends with ".nc" to prevent processing of tagged files
                pattern = r'{}.*{}\.nc$'.format(self.prefix.lower(), field)

                files = utils.get_subset(self.diagsdir, pattern)
                to_archive += utils.add_path(files, self.diagsdir)

        if to_archive:
            for fname in to_archive:
                arch_rtn = self.archive_files(fname)
                self.clean_archived_files(arch_rtn, 'means files')
        else:
            utils.log_msg(' -> Nothing to archive')

    @timer.run_timer
    def archive_restarts(self):
        '''
        Compile list of restart files to archive and subsequently deletes them.
        Rebuild files as necessary on a model by model basis.
        '''
        for rsttype in self.rsttypes:
            final_rst = None

            rstfiles = self.periodfiles(rsttype, 'set')
            if self.suite.finalcycle is not True:
                # Disregard rstfiles produced during "future" cycles of
                # model-run task
                end_of_cycle = self.suite.cyclepoint.endcycle['strlist']
                for filename in reversed(rstfiles):
                    date = self.get_date(filename, enddate=True)
                    if ''.join([str(d).zfill(2) for d in date]) > \
                            ''.join(end_of_cycle):
                        rstfiles.remove(filename)
            rstfiles = sorted(rstfiles)
            to_archive = []
            while len(rstfiles) > self.buffer_archive:
                rst = rstfiles.pop(0)
                if self.suite.finalcycle is True and len(rstfiles) == 0:
                    final_rst = rst
                month, day = self.get_date(rst)[1:3]
                if self.timestamps(month, day) or final_rst:
                    to_archive.append(rst)
                else:
                    msg = 'Only archiving periodic restarts: ' + \
                        str(self.naml.archiving.archive_restart_timestamps)
                    msg += '\n -> Deleting file:\n\t' + str(rst)
                    utils.log_msg(msg)
                    utils.remove_files(rst, path=self.share)

            if to_archive:
                arch_rtn = self.archive_files(to_archive)
                # Do not delete the final restart file following archive
                _ = arch_rtn.pop(final_rst, None)
                self.clean_archived_files(arch_rtn, 'restart files')
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
        for method, archive in self.process_types:
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
    def clean_archived_files(self, archived_files, filetype, path=None):
        '''
        Delete successfully archived files from disk
        Arguments:
            archived_files - <type dict> Return value from self.archive_files -
                                         { <filename>: "SUCCESS"|"FAILED" }
            filetype       - <type str>  Description of filetype
        '''
        # Check for archive failures
        del_files = [fn for fn in archived_files
                     if archived_files[fn] == 'SUCCESS']
        if del_files:
            msg = '{}: deleting archived file(s): \n\t'.format(filetype)
            utils.log_msg(msg + '\n\t'.join(del_files))

            dirname = path if path else os.path.dirname(del_files[0])
            if utils.get_debugmode():
                # Append "ARCHIVED" suffix to files, rather than deleting
                for fname in del_files:
                    if not os.path.dirname(fname):
                        fname = os.path.join(dirname if dirname else self.share,
                                             fname)
                    os.rename(fname, fname.rstrip('_ARCHIVED') + '_ARCHIVED')
            else:
                utils.remove_files(del_files,
                                   path=dirname if dirname else self.share)

    @timer.run_timer
    def compress_file(self, fname, utility, **kwargs):
        '''
        Create command to compress netCDF file
        Arguments:
          fname - Filename to include full path
          utiilty - Compression utility
          kwargs - Dictionary containing command line arguments
        '''
        if utility == 'nccopy':
            rcode = 0
            comp_level = kwargs.pop('compression', 0)
            if comp_level > 0:
                # Check for previous compression with ncdump - do not repeat
                header = self.suite.preprocess_file('ncdump', fname,
                                                    hs='', printout=False)
                if '_DeflateLevel = {}'.format(comp_level) in header:
                    utils.log_msg(
                        'compress_file: {} already compressed '.format(fname) +
                        'with deflation = {}.'.format(comp_level),
                        level='INFO')
                else:
                    rcode = self.suite.preprocess_file(
                        utility, fname,
                        compression=comp_level,
                        chunking=kwargs.pop('chunking', None)
                        )
            else:
                utils.log_msg('compress_file: Deflation = 0 requested.  ' +
                              'No compression necessary for {}'.format(fname),
                              level='INFO')
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
        if self.naml.processing.correct_time_variables or \
                self.naml.processing.correct_time_bounds_variables:
            time_vars = self.naml.processing.time_vars
            if not isinstance(time_vars, (list, tuple)):
                time_vars = [time_vars]

            msg = 'fix_mean_time - Correcting mean time in file: '
            utils.log_msg(msg + meanfile, level='INFO')
            file_log = ''
            for var in time_vars:
                ret_msg = netcdf_utils.fix_times(
                    infiles, meanfile, var,
                    do_time=self.naml.processing.correct_time_variables,
                    do_bounds=self.naml.processing.correct_time_bounds_variables)
                file_log = file_log + ret_msg
            if file_log:
                utils.log_msg(ret_msg, level='OK')
