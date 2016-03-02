#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

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

from collections import OrderedDict

import control
import nlist
import suite
import utils

# Define constants
MM = 'Monthly'
SS = 'Seasonal'
AA = 'Annual'
RR = 'Restarts'

PDICT = OrderedDict([
    (RR, {'Restart': None}),
    (MM, {'Month': None}),
    (SS, {
        'Winter, ending': (('12', 'December'),  ('01', 'January'),
                           ('02', 'February'),  (1,    'YrEnd')),
        'Spring':         (('03', 'March'),     ('04', 'April'),
                           ('05', 'May'),       (0,    'YrEnd')),
        'Summer':         (('06', 'June'),      ('07', 'July'),
                           ('08', 'August'),    (0,    'YrEnd')),
        'Autumn':         (('09', 'September'), ('10', 'October'),
                           ('11', 'November'),  (0,    'YrEnd')),
    }),
    (AA, {'Year': None}),
])


class RegexArgs(object):
    '''
    Container object to hold inputs required to regular expressions
    for use in file templating
    '''
    def __init__(self, field='.*', period='.*',
                 subperiod=None, spvals=None, date=('.*',)*3):
        self.field = field
        self.period = period
        self.subperiod = subperiod
        self.spvals = spvals
        self.date = date


class ModelTemplate(control.runPostProc):
    '''
    Template class for input models
    '''
    __metatclass__ = abc.ABCMeta

    def __init__(self, input_nl='nemocicepp.nl'):
        name = self.__class__.__name__
        self.nl = getattr(nlist.loadNamelist(input_nl), name.lower())
        if self.runpp:
            msg = '{} SHARE: {}'.format(name.upper()[:-8], self.share)
            utils.log_msg(msg)
            msg = '{} WORK: {}'.format(name.upper()[:-8], self.work)
            utils.log_msg(msg)
            self.suite = suite.SuiteEnvironment(self.share, input_nl)
            self.suite.envars = utils.loadEnv('CYLC_SUITE_INITIAL_CYCLE_POINT',
                                              append=self.suite.envars)

    @property
    def runpp(self):
        return self.nl.pp_run

    @property
    def methods(self):
        return OrderedDict([('archive_restarts', self.nl.archive_restarts),
                            ('create_means', self.nl.create_means),
                            ('archive_means', self.nl.archive_means)])

    @property
    def share(self):
        '''
        Share directory - Contains restart data and processed means files.
        '''
        return self.nl.restart_directory

    @property
    def work(self):
        ''' Work directory - Contains unprocessed 10day Means files '''
        return self.nl.means_directory

    @property
    def prefix(self):
        ''' Common filename prefix '''
        return self.suite.prefix

    @property
    def rebuild_cmd(self):
        '''
        Command: Executable + Arguments upto but not including
        the filename(s)
        '''
        try:
            return self.nl.exec_rebuild
        except AttributeError:
            # Not all models require rebuilding
            pass

    def move_to_share(self, pattern=None):
        ''' Move unprocessed means files to SHARE '''
        if pattern:
            workfiles = utils.get_subset(self.work, pattern)
        else:
            # Default pattern - all 10day means files
            inputs = RegexArgs(period=MM)
            workfiles = self.periodset(inputs, datadir=self.work)
        if workfiles:
            utils.log_msg('Moving files to SHARE directory')
            utils.move_files(workfiles, self.share, originpath=self.work)

    def timestamps(self, month, day, process='archive'):
        '''
        Returns True/False - Match a file to given timestamps to establish
        need for processing (rebuild or archive)
        '''
        nlvar = getattr(self.nl, process + '_timestamps')
        if [ts for ts in nlvar if [month, day] == ts.split('-')] or not nlvar:
            valid = True
        else:
            valid = False
        return valid

    @property
    def fields(self):
        return ('',)

    @property
    def rsttypes(self):
        return ('',)

    @abc.abstractproperty
    def set_stencil(self):
        msg = 'SET_STENCIL not implemented. Required return:\n\t'
        msg += 'dict={"period": lambda y,m,s,f: "^{}{}{}{}\.nc$".'\
            'format(y,m,s,f)}'
        utils.log_msg(msg, 4)
        raise NotImplementedError

    @abc.abstractproperty
    def end_stencil(self):
        msg = 'END_STENCIL not implemented. Required return:\n\t'
        msg += 'dict={"period": lambda s,f: "^{}{}\.nc$".format(s,f)}'
        utils.log_msg(msg, 4)
        raise NotImplementedError

    @abc.abstractproperty
    def mean_stencil(self):
        msg = 'MEAN_STENCIL not implemented. Required return:\n\t'
        msg += 'dict={"period": lambda p,y,m,s,f: "^{}{}{}{}{}\.nc$"' \
            '.format(p,y,m,s,f)}'
        utils.log_msg(msg, 4)
        raise NotImplementedError

    @abc.abstractmethod
    def get_date(self, filename):
        msg = 'Model specific get_date method not implemented.\n\t'
        msg += 'return (year, month, day)'
        utils.log_msg(msg, 4)
        raise NotImplementedError

    def periodset(self, inputs, datadir=None, archive=False):
        if not datadir:
            datadir = self.share
        try:
            period = PDICT.keys()[PDICT.keys().index(inputs.period) + 1] if \
                archive else inputs.period
            season = [val[0] for val in inputs.spvals] if \
                inputs.spvals else None
            args = (inputs.date[0], inputs.date[1], season, inputs.field, )
            pattern = self.set_stencil[period](*args)
        except IndexError:
            period = inputs.period
            args = ('.*',)*4
            pattern = self.mean_stencil[period](*args)
            pattern = pattern.replace('.', '\.').replace('\.*', '.*')

        return utils.get_subset(datadir, pattern)

    def periodend(self, inputs, datadir=None, archive=False):
        if not datadir:
            datadir = self.share
        try:
            period = PDICT.keys()[PDICT.keys().index(inputs.period)+1] if \
                archive else inputs.period
            season = [val[0] for val in inputs.spvals] if \
                inputs.spvals else None
            args = (season, inputs.field)
            pattern = self.end_stencil[period](*args)
            return utils.get_subset(datadir, pattern)
        except IndexError:
            return [None, ]

    @staticmethod
    def loop_inputs(fields, archive=False):
        '''
        Generator function for looping over:
          * Fields
          * Periods (years, seasons, months)
          * Subperiods (seasons set)
        '''
        inputs = RegexArgs()
        for field in fields:
            inputs.field = field
            for i, period in enumerate(PDICT.keys()[1:]):
                inputs.period = period
                if archive:
                    use_subp = PDICT.keys()[(i + 2) % len(PDICT)]
                else:
                    use_subp = period
                for subperiod in PDICT[use_subp]:
                    inputs.subperiod = subperiod
                    inputs.spvals = PDICT[use_subp][subperiod]
                    yield inputs

    # *** REBUILD *** #########################################################
    def rebuild_restarts(self):
        pass

    def rebuild_means(self):
        pass

    # *** MEANING *** #########################################################
    @property
    def means_cmd(self):
        '''
        Command: Executable + Arguments upto but not including
        the filename(s)
        '''
        try:
            return self.nl.means_cmd
        except AttributeError:
            raise UserWarning('[FAIL] MEANS exectuable not defined for model.')

    def meantemplate(self, inputs):
        season = [val[0] for val in inputs.spvals] if inputs.spvals else None
        args = (inputs.date[0], inputs.date[1], season, inputs.field)
        return self.mean_stencil[inputs.period](*args)

    @staticmethod
    def describe_mean(inp):
        '''Compose informative description for mean under consideration'''
        MEANS = {
            MM: lambda m, y: ' '.join(m + [y, ]),
            SS: lambda s, y: ' '.join([s, y]),
            AA: lambda a, y: y,
        }
        meantype = ' '.join([inp.field, inp.period])
        subperiod = inp.subperiod if inp.spvals else \
            [m[1] for s in PDICT[SS] for m in PDICT[SS][s] if inp.date[1] in m]
        meandate = MEANS[inp.period](subperiod, inp.date[0])
        return '{} mean for {}'.format(meantype, meandate)

    def create_means(self):
        '''
        Create monthly, seasonal, annual means.
        Delete component files as necessary.
        '''
        if self.work != self.share:
            self.move_to_share()

        # Rebuild means files as required
        self.rebuild_means()

        for inputs in self.loop_inputs(self.fields):
            # Loop over set of means which it should be possible to create
            # from files available.
            for setend in self.periodend(inputs):
                inputs.date = self.get_date(setend)
                describe = self.describe_mean(inputs)
                meanset = self.periodset(inputs)
                if len(meanset) == (4 if inputs.period == AA else 3):
                    # Annual means require 3 component files to be available.
                    # Seasonal and monthly means require 4 components.
                    meanfile = self.meantemplate(inputs)
                    cmd = 'cd {}; {} {} {}'.format(self.share, self.means_cmd,
                                                   (' ').join(meanset),
                                                   meanfile)
                    icode, _ = utils.exec_subproc(cmd)
                    if icode == 0 and os.path.isfile(os.path.join(self.share,
                                                                  meanfile)):
                        msg = 'Created {}: {}'.format(describe, meanfile)
                        utils.log_msg(msg, 2)
                        if inputs.period == MM:
                            msg = 'Deleting 10-day means files used ' \
                                'to create ' + meanfile
                            utils.log_msg(msg)
                            utils.remove_files(meanset, self.share)

                    else:
                        msg = '{}: Error={}'.format(self.means_cmd, icode)
                        utils.log_msg(msg, 4)
                        msg = 'Failed to create {}: {}'.format(describe,
                                                               meanfile)
                        utils.log_msg(msg, 4)
                        utils.catch_failure(self.nl.debug)

                else:
                    # Insuffient component files available to create mean.
                    msg = '{} not possible as only got {} file(s): \n\t{}'.\
                        format(describe, len(meanset), ', '.join(meanset))
                    if self.means_spinup(describe, inputs.date):
                        # Model in spinup period for the given mean.
                        # Insufficent component files is expected.
                        msg = msg + '\n\t -> Means creation in spinup mode.'
                        utils.log_msg(msg, 1)
                    else:
                        utils.log_msg(msg, 4)
                        utils.catch_failure(self.nl.debug)

    def means_spinup(self, description, meandate):
        '''
        A mean cannot be created if the date of the mean is too close the the
        model start time (in the spinup period) to allow all required
        components to be available.
        Returns True if the model is in the spinup period for creation of
        a given mean.
        '''
        initialcycle = self.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT
        first_year = meandate[0] == initialcycle[0:4]

        if first_year:
            if MM in description:
                # Spinup during the first model month if initialised
                # after the first day of a month.
                spinup = int(initialcycle[4:6]) + 1 == int(meandate[1]) and \
                    initialcycle[6:8] != '01'
            elif SS in description:
                # Spinup during the first model season if initialised
                # after the first month of a season.
                mths = [str(int(meandate[1]) - 1).zfill(2),
                        str(int(meandate[1]) - 2).zfill(2)]
                spinup = initialcycle[4:6] in mths
            elif AA in description:
                spinup = True
            else:
                msg = 'means_spinup: unknown meantype requested.\n'
                msg += '\tUnable to assess whether model is in spin up mode.'
                utils.log_msg(msg, 3)
                spinup = False
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
        return self.nl.buffer_archive if self.nl.buffer_archive else 0

    def archive_means(self):
        '''
        Compile list of restart files to archive.
        Only delete if all files are successfully archived.
        '''
        to_archive = []
        for inputs in self.loop_inputs(self.fields, archive=True):
            for setend in self.periodend(inputs, archive=True):
                inputs.date = self.get_date(setend) if setend else (None,)*3
                for mean in self.periodset(inputs, archive=True):
                     to_archive.append(mean)

        if to_archive:
            arch_files = self.archive_files(to_archive)
            if not [fn for fn in arch_files if arch_files[fn] == 'FAILED']:
                msg = 'Deleting archived files: \n\t' + '\n\t'.join(to_archive)
                utils.log_msg(msg)
                utils.remove_files(to_archive, self.share)
        else:
            utils.log_msg(' -> Nothing to archive')

    def archive_restarts(self):
        '''
        Compile list of restart files to archive and subsequently deletes them.
        Rebuild files as necessary on a model by model basis.
        '''
        # Rebuild restart files as required
        self.rebuild_restarts()

        for rsttype in self.rsttypes:
            rstfiles = self.periodset(RegexArgs(period=RR, field=rsttype))
            to_archive = []
            while len(rstfiles) > self.buffer_archive:
                rst = rstfiles.pop(0)
                _, month, day = self.get_date(rst)
                if self.timestamps(month, day):
                    to_archive.append(rst)
                else:
                    msg = 'Only archiving periodic restarts.'
                    msg += '\n -> Deleting file:\n\t' + str(rst)
                    utils.log_msg(msg)
                    utils.remove_files(rst, self.share)

            if to_archive:
                arch = self.archive_files(to_archive)
                to_delete = [fn for fn in arch if arch[fn] == 'SUCCESS']
                msg = 'Deleting archived files: \n\t' + '\n\t'.join(to_delete)
                utils.remove_files(to_delete, self.share)
            else:
                msg = ' -> Nothing to archive'
                if rstfiles:
                    msg = '{} - {} restart{} files available ({} retained).'.\
                        format(msg, len(rstfiles), rsttype,
                               self.buffer_archive)
            utils.log_msg(msg)

    def archive_files(self, filenames):
        '''
        Archive a one or more files.
        Returns a dictionary of requested files reporting success or failure.
        '''
        returnfiles = {}
        if type(filenames) != list:
            filenames = [filenames]

        for fname in filenames:
            rcode = self.suite.archive_file(fname, debug=self.nl.debug)
            if rcode == 0:
                utils.log_msg('Archive successful.', 2)
                returnfiles[fname] = 'SUCCESS'
            else:
                msg = 'Failed to archive file: {}. Will try again later.'.\
                    format(fname)
                returnfiles[fname] = 'FAILED'
                utils.log_msg(msg, 3)

        return returnfiles
