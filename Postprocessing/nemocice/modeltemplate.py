#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
(C) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
*****************************COPYRIGHT******************************
--------------------------------------------------------------------
 Code Owner: Please refer to the UM file CodeOwners.txt
 This file belongs in section: Rose scripts
--------------------------------------------------------------------
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
            msg = '{} SHARE directory: {}'.format(name.upper()[:-8], self.share)
            utils.log_msg(msg)
            msg = '{} WORK directory: {}'.format(name.upper()[:-8], self.work)
            utils.log_msg(msg)
            self.suite = suite.SuiteEnvironment(self.share, input_nl)

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
    @staticmethod
    def rebuild_restarts():
        pass

    @staticmethod
    def rebuild_means():
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
            for setend in self.periodend(inputs):
                inputs.date = self.get_date(setend)
                describe = self.describe_mean(inputs)
                meanset = self.periodset(inputs)
                if len(meanset) == (4 if inputs.period == AA else 3):
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
                    msg = '{} not possible as only got {} file(s).'.\
                        format(describe, len(meanset)), meanset
                    utils.log_msg(msg)
                    if inputs.period == MM:
                        utils.log_msg(' -> Files will be deleted...')
                        utils.remove_files(meanset, self.share)

    # *** ARCHIVING *** #######################################################
    @property
    def buffer_archive(self):
        '''
        Number of unprocessed files to retain after archiving
        task is complete
        '''
        return self.nl.buffer_archive if self.nl.buffer_archive else 0

    def archive_means(self):
        archive_required = False
        for inputs in self.loop_inputs(self.fields, archive=True):
            for setend in self.periodend(inputs, archive=True):
                inputs.date = self.get_date(setend) if setend else (None,)*3
                for mean in self.periodset(inputs, archive=True):
                    archive_required = True
                    self.archive_file(mean)
        if not archive_required:
            utils.log_msg(' -> Nothing to archive')

    def archive_restarts(self):
        # Rebuild restart files as required
        self.rebuild_restarts()

        for rsttype in ['', '\.age']:
            rstfiles = self.periodset(RegexArgs(period=RR, field=rsttype))
            archive_required = len(rstfiles) > self.buffer_archive
            while len(rstfiles) > self.buffer_archive:
                archive_required = True
                rst = rstfiles.pop(0)
                _, month, day = self.get_date(rst)
                if self.timestamps(month, day):
                    self.archive_file(rst)
                else:
                    msg = 'Only archiving periodic restarts.'
                    msg += '\n -> Deleting file:\n\t' + str(rst)
                    utils.log_msg(msg)
                    utils.remove_files(rst, self.share)
            if rstfiles and not archive_required:
                msg = ' -> Nothing to archive. {} restart{} files available.'.\
                    format(len(rstfiles), rsttype)
                msg += ' ({} retained).'.format(self.buffer_archive)
                utils.log_msg(msg)

    def archive_file(self, rst):
        rcode = self.suite.archive_file(rst, debug=self.nl.debug)
        if rcode == 0:
            utils.log_msg('Archive successful.', 2)
            utils.log_msg('Deleting file: ' + rst)
            utils.remove_files(rst, self.share)
        else:
            msg = 'Failed to archive file: {}. Will try again later.'.\
                format(rst)
            utils.log_msg(msg, 3)
