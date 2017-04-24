#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    netcdf_filenames.py

DESCRIPTION
    Module containing methods to ensure the Met Office filenaming conventions
    for netCDF output are maintained in the archive
'''
import os
import re

import utils

NCF_REGEX = r'^{P}_{B}_{S}-{E}{C}\.nc$'
NCF_TEMPLATE = NCF_REGEX.lstrip('^').rstrip(r'\.nc$') + '.nc'


class NCFilename(object):
    r'''
    Container object for the variables in a netCDF filename
    Optional arguments:
      base      : Format should be r'\d*\w+'.
                  Default=r'\d+[hdmsyx]{1}' - to match any standard mean
                  frequency identifier (as per NCF convention).
                  Used in:
                     * Calculation of the end date for a given start date.
                     * Regular expressions to match one or more frequency
                       identifiers in filenames.
                     * In a filename template to set the frequency identifier.
      start_date: Tuple, length=3.
                  Default=(r'\d{4}', r'\d{2}', r'\d{2}') to match any date -
                  mainly used in calls to  mean_stencil() when archiving.
    '''
    def __init__(self, model, suite, realm, base=r'\d+[hdmsyx]{1}',
                 start_date=(r'\d{4}', r'\d{2}', r'\d{2}'), custom=''):
        r'''
        Initialise container:
            Arguments:
                model - lowercase string indicating model component
                suite - lowercase string indicating the suitename prefix to
                        model output filenames
                realm - single character (lowercase) indicating the model realm
            Optional Arguments:
                base       - Default value r'\d+\w+' may be used when creating a
                    regular expression for all mean files of a given prefix
                    and/or custom field.
                start_date - Should be a tuple([<type str>,]*3).
                    Default value (r'\d{4}', r'\d{2}', r'\d{2}') may be used
                    when creating a regular expression for all files of a given
                    prefix/base/custom field.
        '''
        self.prefix = self._prefix(model, suite, realm)
        self.base = base
        self.start_date = start_date
        self.custom = custom

    def _prefix(self, component, suitename, realm):
        '''
        Return the filename prefix - independent of datestamp.
        Component and suitename should be lowercase.
        Suitenames should be changed to replace any '_' or '.' with '-'.
        '''
        suitename = suitename.replace('_', '-').replace('.', '-')
        return '{C}_{S}{R}'.format(C=component.lower(),
                                   S=suitename.lower(),
                                   R=realm.lower())

    def calc_enddate(self, target=None):
        '''
        Return the end date of the filename object.
        Optional argument:
           target = Given when the end date to be calculated is not self.base
                    ahead of the start_date - for example one month's worth
                    of daily means concatenated into a single file.
        '''
        target = target if target else self.base
        return calc_enddate(self.start_date, target)

    @staticmethod
    def nc_match(fname):
        '''
        Return a logical indicator as to whether a filename is compliant with
        the Met Office netCDF filename convention:
        <model>_<suite>_<frequency>_<startdate>-<enddate>_<custom><proc_id>.nc
       '''
        model = r'[\-\da-z]+'
        suite = r'[\-\da-z]+[aio]'
        freq = r'\d*[xysmdh]+'
        date = r'\d{6,10}'
        custom = r'(_[\-\da-zA-Z]+)?'
        proc_id = r'(_\d*)?'
        pattern = NCF_REGEX.format(P='_'.join([model, suite]), B=freq, S=date,
                                   E=date, C=custom + proc_id)
        return bool(re.match(pattern, fname))

    def rename_ncf(self, fname, target=None):
        '''
        netCDF files are to be archived with a Met Office agreed filenaming
        convention:
        <model>_<suite>_<frequency>_<startdate>-<enddate>_<custom>.nc

        <model>     - model name.
                      Lowercase alphanumeric plus "-". Controlled value list.
        <suite>     - char, + 1char for UM realm represented by model.
                      Lowercase alphanumeric plus "-".
                      Realm from controlled value list.
        <frequency> - Data frequency.
                      Time unit in lowercase and from controlled list.
        <***date>   - Date scheme following CMOR-like conventions.
                      6-10 digits YYYYMM[DD[HH]] as received from the model.
                      CF convention used for enddate.
        <custom>    - Custom field, for example grid type indicator
                      Mixed-case alphanumeric plus "-".
                      If the incoming file is a component of a complete file
                      which requires subsequent rebuilding, the custom field may
                      be suffixed with a processor ID.
        Arguments:
          fname - Incoming filename
          target (Optional) - Required when the end date to be calculated is not
                              simply self.base ahead of self.start_date but,
                              most likely, some multiple of it.
        '''

        if self.nc_match(os.path.basename(fname)):
            return
        startdate = ''.join(self.start_date)
        enddate = ''.join(self.calc_enddate(target=target if target
                                            else self.base))
        if len(startdate) == 6:
            startdate += '01'
            enddate += '01'

        custom = '_' + self.custom if self.custom else ''
        newfname = NCF_TEMPLATE.format(P=self.prefix, B=self.base, S=startdate,
                                       E=enddate, C=custom)

        msg = 'netcdf_filenames.netcdf_fname: Renaming {} as {}'
        utils.log_msg(msg.format(fname, newfname))
        try:
            os.rename(fname, os.path.join(os.path.dirname(fname), newfname))
        except OSError:
            msg = 'netcdf_filenames.netcdf_fname: Failed to rename file: {}'
            # Raise 'ERROR' - System exit unless in debug mode.
            utils.log_msg(msg.format(fname), level='ERROR')


def ncf_getdate(filename, enddate=False):
    '''
    Return the date extracted from the filename provided.
    By default, the start date for the data is returned.
    '''
    def datestrings():
        ''' Generator function extracting datestrings from a filename. '''
        datestrings = [ds for ds in re.split(r'[._\-]', filename)
                       if re.match(r'^\d{6,10}$', ds)]
        for dstring in datestrings:
            splitdate = re.match(r'(\d{4})(\d{2})(\d{2})?(\d{2})?',
                                 dstring).groups()
            yield [d for d in splitdate if d]

    dates = [tuple(d) for d in datestrings()]
    if len(dates) == 0:
        rtndate = None
    else:
        rtndate = dates[-1] if len(dates) == 1 or enddate else dates[-2]
    return rtndate


def calc_enddate(startdate, target, freq=1):
    r'''
    Return the end date given a start_date and a target period.
    Default end date calculated is self.base ahead of self.start_date.
    Arguments:
        startdate - Tuple or list: (YYYY, MM, DD, [mm], [hh])
        target    - Target period from startdate.
                    A valid target should match r'-?\d*[hdmsyxHDMSYX].*' to
                    give one of [hour(s), day(s), month(s), season(s),
                                 year(s), decade(s)].
                    The valid target string may be prefixed with a frequency
                    digit.
    Optional arguments:
        freq      - Default=1.
                    Used as a multiplier to self.base or target when
                    given without digit prefix.
    '''
    indate = list(startdate)
    while len(indate) < 3:
        indate.append('01')
    while len(indate) < 5:
        indate.append('00')

    digit, char = utils.get_frequency(target)
    rtndate = utils.add_period_to_date(indate,
                                       '{}{}'.format(digit * freq, char))
    # Truncate rtndate at the same length as start_date
    rtndate = [str(i).zfill(2) for i in rtndate[0:len(startdate)]]
    return tuple(rtndate)


def seasonend(meanref):
    '''
    Return a tuple of 4 string MMDD representations for the season ends.
    '''
    seasons = []
    while len(seasons) < 4:
        seasons.append((meanref[1] + (len(seasons) * 3)) % 12)
    try:
        # Replace any instance of '0' with '12' for December
        seasons[seasons.index(0)] = 12
    except ValueError:
        pass
    for i, _ in enumerate(seasons):
        # Modify to return tuple of strings
        seasons[i] = str(seasons[i]).zfill(2) + str(meanref[2]).zfill(2)
    return tuple(sorted(seasons))


def period_end(period, fvars, meanref):
    '''
    Return a regular expression to match the last file in set for a given
    period mean.
    Date stamps will be calculated based on the mean reference date
    and the base component of the period mean (fn_vars.base)

    The presence of the "end" file indicates that all components of the
    period mean must logically exist.

    Arguments:
        period <type str>       - Target period. One of ['1m', '1s', '1y']
        fvars <type NCFilename> - fvars.base should either be a base frequency
                                  (e.g. 6h, 10d, 1m)
        meanref <type list>     - Mean reference date
    '''
    try:
        freq, base = re.match(r'(\d+)([a-z]+)', fvars.base).groups()
    except AttributeError:
        freq = '1'
        base = fvars.base[0].lower()

    if period == '1m':
        end_mmdd = r'\d{{2}}{:02}'.format(meanref[2])
    elif period == '1s':
        end_mmdd = '|'.join(seasonend(meanref))
    elif period == '1y':
        end_mmdd = str(meanref[1]).zfill(2) + str(meanref[2]).zfill(2)
    else:
        # Period not recognised
        end_mmdd = 'MMDD'
        msg = 'netcdf_filenames: period_end - Mean period {} not recognised.'
        msg += '  Defaulting to start date "MMDD"'
        utils.log_msg(msg.format(period), level='WARN')

    return NCF_REGEX.format(P=fvars.prefix, B=''.join([freq, base]),
                            S=r'\d{8,10}',
                            E=r'\d{{4}}({})(00)?'.format(end_mmdd),
                            C=fvars.custom)


def period_set(period, fvars):
    '''
    Return a regular expression to match any file in a given mean set.

    The start and end dates of the set are defined by the
    start date and base frequency attributes of end-of-period file.

    Arguments:
        period <type str>       - One of '1m', '1s', '1y'
        fvars <type NCFilename> - The representation of the end-of-period file
                                  in the mean set.
                                  fvars.base should be a base frequency
                                  (e.g. 6h, 10d, 1m)
    '''
    end_yyyymmdd = calc_enddate(fvars.start_date, fvars.base)
    # Calculate the startdate for the period
    start_yyyymmdd = [calc_enddate(end_yyyymmdd, '-' + period)]

    while ''.join(start_yyyymmdd[-1]) < ''.join(end_yyyymmdd):
        # Calculate all start date options stepping through from
        # start to end date of the period, with step length = fvars.base
        start_yyyymmdd.append(calc_enddate(start_yyyymmdd[-1], fvars.base))
        if len(start_yyyymmdd) > 50:
            # Catch too many date options - break out of loop
            msg = 'netcdf_filenames: period_set - Too many start date options: '
            msg += '{} set with {} base component.'.format(period, fvars.base)
            utils.log_msg(msg, level='WARN')
            break

    start_set = '|'.join([''.join(d) for d in start_yyyymmdd[:-1]])
    return NCF_REGEX.format(P=fvars.prefix, B=fvars.base,
                            S=r'({})(\d{{2}})?'.format(start_set),
                            E=r'\d{8,10}', C=fvars.custom)


def mean_stencil(fvars, target=None):
    r'''
    Return a stencil for the creation of a given mean filename.

    The end date for the mean filename is calculated based on the
    start date and base frequency attributes of the fvars object argument.

    Arguments:
       fvars - An object of <type NCFilename>
             - Where fvars.start_date = ('\d{4}')*3 a regular expression
               to match all dates will be returned
    '''
    startdate = fvars.start_date
    # For "all files" stencil, startdate will be ('\d{4}', '\d{2}', '\d{2}')
    if startdate[0] == r'\d{4}':
        enddate = startdate
    else:
        target = target if target else fvars.base
        enddate = calc_enddate(fvars.start_date, target)

    return NCF_TEMPLATE.format(P=fvars.prefix, B=fvars.base,
                               S=''.join(startdate), E=''.join(enddate),
                               C=fvars.custom)
