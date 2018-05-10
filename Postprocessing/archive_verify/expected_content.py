#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    archived_files.py

DESCRIPTION
    Parent class for methods used to calculate archived filenames
'''

import re

import filenames
import utils

MONTHS = {
    1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr',
    5: 'may', 6: 'jun', 7: 'jul', 8: 'aug',
    9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
}


def nlist_date(date, description):
    ''' Obtain an integer date list [YYYY, MM}, DD] from an 8 digit string '''
    date = str(date).zfill(8)
    try:
        datelist = re.match(r'(\d{4})(\d{2})(\d{2})(\d{2})?',
                            str(date)).groups()
    except AttributeError:
        utils.log_msg('Namelist read error.  {} should consist of 8-10'
                      ' digits: "{}"'.format(description, date), level='FAIL')

    datelist = [int(x) for x in datelist if x]
    if len(datelist) < 3:
        datelist.append(1)
    return datelist


def atmos_stream_items(naml):
    '''
    Atmosphere stream IDs should be two character.
    Format = [pm][a-z0-9]
    Single character namelist input is accepted, in which case the
    first character is assumed to be "p".
    Arguments:
       naml - <type utils.Variables> Namelist object
    '''
    stream_namelists = [a for a in dir(naml) if
                        a.startswith('streams') or a.endswith('_streams')]

    for namelist in stream_namelists:
        val = getattr(naml, namelist)
        newval = []
        if val:
            for stream_id in utils.ensure_list(val):
                # Default to 'p' prefix for single character streams
                stream_id = str(stream_id)
                if len(stream_id) == 1:
                    stream_id = 'p' + stream_id
                elif len(stream_id) != 2:
                    utils.log_msg(
                        'Unidentifiable atmosphere streamID '
                        '"{}" in &atmosverify/{}'.format(stream_id, namelist),
                        level='ERROR'
                        )
                newval.append(stream_id)
        setattr(naml, namelist, newval)

    return naml


class ArchivedFiles(object):
    '''
    Methods specific to determining filenames expected to be present
    in the archive.
    '''
    def __init__(self, startdate, enddate, prefix, model, naml):
        ''' Initialise ArchiveFiles methods '''
        self.sdate = nlist_date(startdate, 'Start date')
        self.edate = nlist_date(enddate, 'End date')
        self.prefix = prefix
        self.model = model
        if self.model == 'atmos':
            naml = atmos_stream_items(naml)
        self.naml = naml
        self.meanref = None
        self.finalcycle = utils.finalcycle()

    def extract_date(self, filename, start=True):
        '''
        Extract integer year, month and day from filename.
        '''

        date_patterns = (r'\d{4}[a-z]{3}', r'\d{8}_\d{2}', r'\d{6,10}',
                         r'\d{4}-\d{2}-\d{2}-\d{2}?-?')
        for patt in date_patterns:
            dates = re.findall(patt, filename)
            if dates:
                break
        splits = []
        for date in dates:
            if '-' in date:
                splits.append(date.split('-'))
            else:
                splits.append(re.match(r'(\d{4})(\d{2}|[a-z]{3})'
                                       r'(\d{2})?(\d{2})?_?(\d{2})?',
                                       date).groups())

        date = splits[0] if start else splits[-1]
        year, month = date[:2]
        if re.match(r'([a-z]{3})', month):
            # Special case for atmosphere monthly and seasonal files
            try:
                # Monthly files
                month = MONTHS.keys()[MONTHS.values().index(month)]
            except ValueError:
                # Seasonal files
                try:
                    for mth, ssn in self.seasons(self.meanref):
                        if month == ssn:
                            month = mth
                            break
                except TypeError:
                    utils.log_msg('Mean reference date required for '
                                  'seasonal mean date.', level='FAIL')
                # Seasonal datestamp year is FINAL month
                if month > 9:
                    year = int(year) - 1
                if not start:
                    month += 3
                    if month > 12:
                        month -= 12
                        year = int(year) + 1

        day = date[2] if date[2] else 1
        int_date = [int(year), int(month), int(day)]
        for i in range(3, 6):
            if len(date) > i:
                if date[i]:
                    int_date.append(int(date[i]))

        return int_date

    def seasons(self, meanref, shift=0):
        '''
        Return a list of tuples: (starting month, 3char descriptor) for
        each season.
        '''
        seasons = []
        while len(seasons) < 4:
            seasons.append((meanref[1] + shift + (len(seasons) * 3)) % 12)
        try:
            seasons[seasons.index(0)] = 12
        except ValueError:
            pass
        for i, ssn in enumerate(seasons):
            # Modify to list of tuples [tuple(start month, descriptor)]
            months = MONTHS[ssn][0]
            for mth in [1, 2]:
                months += MONTHS[ssn + mth if ssn + mth <= 12 else
                                 ssn + mth - 12][0]
            seasons[i] = (ssn, months)

        return sorted(seasons)

    def get_collection(self, period=None, stream=None):
        '''
        Return Moose collection name appropriate to stream.
        '''
        key, realm, component = self.get_fn_components(stream)
        if component:
            try:
                stream = period[-1]
            except TypeError:
                # Period is None. atmos ncf_mean takes streamID
                stream = stream[-1]

        collection = filenames.COLLECTIONS[key].format(R=realm, S=stream)
        return collection

    def get_fn_components(self, stream):
        '''
        Construct the dictionary key for filenames module.
        '''
        realm, component = filenames.model_components(self.model, stream)

        if component:
            # "component" is only relevant to the netCDF convention filenames
            key = 'ncf_mean'
        elif stream:
            # Atmosphere fields/pp files
            if str(stream) in self.naml.ff_streams:
                key = 'atmos_ff'
            else:
                key = 'atmos_pp'
        else:
            key = 'rst'

        return key, realm, component


class RestartFiles(ArchivedFiles):
    '''
    Methods specific to determining restart filenames expected to be present
    in the archive.
    '''
    def __init__(self, startdate, enddate, prefix, model, naml):
        ''' Initialise ArchiveFiles methods '''
        super(RestartFiles, self).__init__(startdate, enddate, prefix,
                                           model, naml)
        self.timestamps = self._timestamps()
        try:
            dump_delay = naml.delay_rst_archive
        except AttributeError:
            # No delay in restart file archive
            dump_delay = '0d'
        self.sdate = utils.add_period_to_date(self.sdate[:], dump_delay)
        self.rst_types = ['{}_rst'.format(model)]
        for rst in [a for a in dir(naml) if a.endswith('_rst')]:
            if getattr(self.naml, rst):
                self.rst_types.append(rst)

    def _timestamps(self):
        ''' Return a list of timestamps '''
        meanref = nlist_date(self.naml.mean_reference_date,
                             'mean reference date')
        seasons = [s[0] for s in self.seasons(meanref)]
        if 'Monthly' in self.naml.archive_timestamps:
            tstamps = [[x, meanref[2]] for x in range(1, 13)]
        elif 'Seasonal' in self.naml.archive_timestamps:
            tstamps = [[x, meanref[2]] for x in seasons]
        elif 'Annual' in self.naml.archive_timestamps:
            tstamps = [[meanref[1], meanref[2]]]
        elif 'Biannual' in self.naml.archive_timestamps:
            tstamps = [[max(seasons) - 6, meanref[2]],
                       [max(seasons), meanref[2]]]
        else:
            nlist_stamps = utils.ensure_list(self.naml.archive_timestamps)
            try:
                tstamps = [[int(x) for x in tstamp.split('-')]
                           for tstamp in nlist_stamps]
            except ValueError:
                utils.log_msg('Restart Files - Format for archive_timestamps'
                              ' should be "MM-DD"[, "MM-DD"]', level='FAIL')
        return tstamps

    def expected_files(self):
        ''' Generate a list of expected restart files '''
        restart_files = {}
        try:
            suffix = self.naml.restart_suffix
        except AttributeError:
            suffix = None

        utils.log_msg('Restart files - expected files for {} at timestamps'
                      ' {}:'.format(self.model, self.timestamps), level='INFO')
        coll = self.get_collection()
        for year in range(self.sdate[0], self.edate[0] + 1):
            for tstamp in self.timestamps:
                for rsttype in self.rst_types:
                    newfile = self.get_filename(year, tstamp[0], tstamp[1],
                                                suffix, rsttype)
                    try:
                        restart_files[coll].append(newfile)
                    except KeyError:
                        restart_files[coll] = [newfile]

        restart_files[coll] = self.remove_invalid(restart_files[coll])

        if self.finalcycle:
            # Additionally archive the end date dump
            year, month, day = self.edate
            if 30 in self.timestamps[0]:
                # Account for NEMO last-day datestamp
                day = 30
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
            for rsttype in self.rst_types:
                final_rst = self.get_filename(year, month, day, suffix, rsttype)
                if final_rst not in restart_files[coll]:
                    restart_files[coll].append(final_rst)

        for key in restart_files.keys():
            # Call to keys() required as we are removing dictionary keys
            if restart_files[key] == []:
                del restart_files[key]

        return restart_files

    def remove_invalid(self, restart_files):
        '''
        Remove files with datestamps before or after the specified
        start/end date.
        '''
        edate = self.edate[:]
        if not self.finalcycle and hasattr(self.naml, 'buffer_restart'):
            # Adjust for mean buffer
            cycletime = utils.CylcCycle().startcycle['iso']
            edate_str = [str(x).zfill(2) for x in edate]
            while len(edate_str) < 5:
                edate_str.append('00')
            endtime = '{}{}{}T{}{}Z'.format(*edate_str[:5])
            cmd = 'rose date {} {} --calendar {}'.format(endtime, cycletime,
                                                         utils.calendar())
            rcode, cyclefreq = utils.exec_subproc(cmd, verbose=False)
            if rcode == 0:
                rst_buffer = self.naml.buffer_restart
                while rst_buffer and rst_buffer > 1:
                    edate = utils.add_period_to_date(edate, cyclefreq)
                    rst_buffer -= 1

            else:
                utils.log_msg('restart buffer - unable to calculate cycling '
                              'period. Reverting to buffer_restart=1',
                              level='WARN')

        to_remove = []
        for filename in restart_files:
            filedate = self.extract_date(filename, start=True)
            year, month, day = filedate[:3]

            if year < self.sdate[0] or year > edate[0]:
                to_remove.append(filename)
            else:
                if year == self.sdate[0]:
                    # Remove files prior to and including the start date
                    if month < self.sdate[1] or \
                            (month == self.sdate[1] and day <= self.sdate[2]):
                        to_remove.append(filename)

                if year == edate[0]:
                    # Remove files at and after the end date
                    if month > edate[1] or \
                            (month == edate[1] and day >= edate[2]):
                        to_remove.append(filename)

        # Remove duplicates from to_remove before thinning restart_files list
        for filename in list(set(to_remove)):
            restart_files.remove(filename)

        return restart_files

    def get_filename(self, year, month, day, suffix, rsttype):
        '''
        Return filename according to filenames.FNAMES regular expression.
        Arguments:
           year, month, day
           suffix = required where an optional file suffix is present (CICE)
        '''
        return filenames.FNAMES[rsttype].format(P=self.prefix, Y1=year,
                                                M1=month, D1=day, S=suffix)


class DiagnosticFiles(ArchivedFiles):
    '''
    Methods specific to determining means filenames expected to be present
    in the archive.
    '''
    def __init__(self, startdate, enddate, prefix, model, naml):
        ''' Initialise MeansFiles methods '''
        super(DiagnosticFiles, self).__init__(startdate, enddate,
                                              prefix, model, naml)
        fields = self.naml.meanfields if self.naml.meanfields else ''
        self.meanfields = utils.ensure_list(fields, listnone=True)

        self.meanref = nlist_date(self.naml.mean_reference_date,
                                  'mean reference date')
        self.tlim = self.time_limited_streams()

    def gen_reinit_period(self, reinit_periods):
        '''
        Generator method to yield reinitialisation step and period
        for each stream.
        '''
        for reinit in reinit_periods:
            # In the case of concatenated files, delta follows '_'
            # Otherwise it is the same as the base frequency
            base = reinit.replace('streams_', '').split('_')[0]
            delta = reinit.split('_')[-1]

            if reinit in dir(self.naml):
                descript = 'instantaneous'
                streams = utils.ensure_list(getattr(self.naml, reinit))
                if len(streams) == 1 and streams[0] is True:
                    # Allow for blank field name
                    streams = ['']
            else:
                descript = 'mean'
                if self.model == 'atmos':
                    streams = ['p' + reinit[-1]]
                else:
                    streams = self.meanfields

            if streams:
                yield base, delta, list(set(streams)), descript

    def get_period_startdate(self, period, refday=True):
        '''
        Return the date of the first file which should be produced
        for the period provided according to the mean reference date.

        Arguments:
            period = single char from [hdmsyx]
        Optional arguments:
            refday <type bool> = Use the mean reference day for the period start
        '''
        sdate = self.sdate[:]
        while len(sdate) < 5:
            sdate.append(0)

        if period not in 'dh' and refday:
            sdate[2] = self.meanref[2]
            if self.sdate[2] > sdate[2]:
                sdate[1] += 1
                if sdate[1] > 12:
                    sdate[1] -= 12
                    sdate[0] += 1

        if period == 's':
            s_starts = [s[0] for s in self.seasons(self.meanref)]
            while sdate[1] not in s_starts:
                sdate[1] += 1
                if sdate[1] > 12:
                    sdate[1] -= 12
                    sdate[0] += 1
        elif period in 'yx':
            sdate[1] = self.meanref[1]
            if sdate[1] < self.sdate[1]:
                sdate[0] += 1
            if period == 'x':
                sdate[0] = self.meanref[0]
                while sdate[0] < self.sdate[0]:
                    sdate[0] += 10

        return sdate

    def expected_diags(self):
        ''' Generate a list of expected diagnostic output files '''
        all_files = {}
        intermittent_coll = {}

        all_streams = [a for a in dir(self.naml) if a.startswith('streams')]
        all_streams += utils.ensure_list(self.naml.meanstreams)
        try:
            spawn_ncf = utils.ensure_list(self.naml.spawn_netcdf_streams)
        except AttributeError:
            spawn_ncf = []
        try:
            intermittent_streams = \
                utils.ensure_list(self.naml.intermittent_streams)
            intermittent_patterns = \
                utils.ensure_list(self.naml.intermittent_patterns)
        except AttributeError:
            intermittent_streams = []

        for base, delta, streams, desc in \
                self.gen_reinit_period(list(set(all_streams))):
            date = self.get_period_startdate(delta[-1])
            edate = self.edate[:]
            while len(edate) < 5:
                edate.append(0)

            if not self.finalcycle and hasattr(self.naml, 'buffer_mean'):
                # Adjust for mean buffer
                mean_buffer = self.naml.buffer_mean
                while mean_buffer and mean_buffer > 0:
                    edate = utils.add_period_to_date(
                        edate, '-{}'.format(self.naml.base_mean)
                        )
                    mean_buffer -= 1

            while date <= edate:
                newdate = utils.add_period_to_date(date, delta)

                add_file = True
                if desc == 'instantaneous' and self.model == 'atmos':
                    # Atmos instantaneous streams not available at the edate
                    # due to reinitialisation method.
                    if date == edate:
                        add_file = False
                elif newdate > edate:
                    # newdate is end of data so must fall before edate.
                    add_file = False

                if add_file:
                    if self.model == 'atmos' and desc == 'mean':
                        # Adjust year for atmosphere means - use end year
                        if newdate[1:3] > [1, 1]:
                            date[0] = newdate[0]
                    for stream in streams:
                        stream = str(stream)
                        if stream in self.tlim and \
                                (date < self.tlim[stream][0] or
                                 date >= self.tlim[stream][1]):
                            # Time limited stream - outside output dates
                            continue

                        coll = self.get_collection(period=base, stream=stream)
                        if stream in intermittent_streams:
                            intermittent_coll[coll] = stream
                        newfile = self.get_filename(base, date, newdate, stream)
                        try:
                            all_files[coll].append(newfile)
                        except KeyError:
                            all_files[coll] = [newfile]

                        if stream in spawn_ncf:
                            spawn_coll = self.get_collection(
                                period=stream,
                                stream=filenames.FIELD_REGEX
                                )
                            if stream in intermittent_streams:
                                intermittent_coll[spawn_coll] = stream

                            spawnfile = self.get_filename(
                                r'\d+[hdmsyx]', date, newdate, stream + 'ncf'
                                )
                            spawnfile = spawnfile.replace('.nc', r'\.nc$')
                            try:
                                all_files[spawn_coll].append(spawnfile)
                            except KeyError:
                                all_files[spawn_coll] = [spawnfile]

                date = newdate

        for fileset in all_files:
            if not self.finalcycle:
                try:
                    if re.match(r'^a[pmn]([a-zA-Z0-9])\.',
                                fileset).group(1) not in 'msyx':
                        # Atmosphere instantaneous pp/fieldsfiles
                        if (fileset[2] in self.tlim) and \
                                (self.tlim[fileset[2]][1] < self.edate):
                            # Time limited period is over - no file waiting
                            # for reinitialisation.
                            pass
                        else:
                            all_files[fileset].remove(all_files[fileset][-1])
                except AttributeError:
                    if fileset[2] in 'dmsyx':
                        all_files[fileset] = self.remove_higher_mean_components(
                            all_files[fileset], fileset[2]
                            )

            if fileset in intermittent_coll:
                pattern = intermittent_patterns[
                    intermittent_streams.index(intermittent_coll[fileset])
                    ]
                for i, fname in enumerate(all_files[fileset][:]):
                    if pattern[i % len(pattern)] == 'x':
                        all_files[fileset].remove(fname)

        all_files.update(self.iceberg_trajectory())

        for key in all_files.keys():
            # Call to keys() required since we are removing dictionary keys
            if all_files[key] == []:
                del all_files[key]

        return all_files

    def remove_higher_mean_components(self, periodfiles, period):
        '''
        Where available means files can be used to create higher means they
        will not be found in the archive until that higher mean has been
        created.
        '''
        meanstreams = utils.ensure_list(self.naml.meanstreams)
        skip = ''
        meanperiods = 'xysmd'
        period_id = meanperiods.index(period)
        topmean = True
        for mean in meanperiods[:period_id]:
            if '1' + mean in meanstreams:
                topmean = False
            else:
                skip += mean

        period_condition = meanperiods[period_id]
        if skip:
            shift = 1
            try:
                while meanperiods[period_id - shift] in skip:
                    period_condition = meanperiods[period_id - shift]
                    shift += 1
            except IndexError:
                # No further periods
                pass

        meansfiles = [fn for fn in reversed(periodfiles) if
                      any([fd in fn for fd in self.meanfields])]

        to_remove = []
        season_starts = [m for m, _ in self.seasons(self.meanref)]
        for fname in meansfiles:
            year, month, day = self.extract_date(fname, start=False)[:3]
            conditions = {
                'd': day == self.meanref[2],
                'm': month in season_starts and day == self.meanref[2],
                's': [month, day] == self.meanref[1:3],
                'y': [month, day] == self.meanref[1:3] and \
                    str(year)[-1] == str(self.meanref[0])[-1],
                'x': True,
                }
            if topmean or conditions[period_condition]:
                break
            else:
                to_remove.append(fname)

        for fname in to_remove:
            periodfiles.remove(fname)

        return periodfiles

    def time_limited_streams(self):
        '''
        Return a dictionary of Atmosphere time-limited streams.
           { stream_id (2Char) : tuple(
                                       startdate (integer list [YYYY, MM, DD]),
                                       enddate (integer list [YYYY, MM, DD])
                                      )
           }

        Based on namelist variables:
           bool     : timelimitedstreams
           str list : tlim_streams (2char)
           str list : tlim_starts (8char)
           str list : tlim_ends (8char)
        '''
        time_limited = {}
        try:
            tlim = self.naml.timelimitedstreams
        except AttributeError:
            tlim = False

        if tlim:
            streams = utils.ensure_list(self.naml.tlim_streams)
            if streams:
                startdates = utils.ensure_list(self.naml.tlim_starts)
                enddates = utils.ensure_list(self.naml.tlim_ends)

                if (len(streams) != len(startdates)) or \
                        (len(streams) != len(enddates)):
                    utils.log_msg('Time-limited streams:  Please ensure start '
                                  'and end dates are provided for each '
                                  'time-limited stream.', level='FAIL')

                for i, stream in enumerate(streams):
                    start = nlist_date(startdates[i],
                                       'time limited stream start date')
                    end = nlist_date(enddates[i],
                                     'time limited stream end date')
                    time_limited[stream] = (start, end)

        return time_limited

    def iceberg_trajectory(self):
        '''
        Return list of expected nemo iceberg trajectory files
        '''
        fileset = 'oni.nc.file'
        iceberg_traj = {fileset: []}
        try:
            iberg = self.naml.iberg_traj
        except AttributeError:
            iberg = False

        if iberg:
            freq = self.naml.iberg_traj_freq
            date = self.sdate + [0, 0]
            edate = self.edate + [0, 0]

            fmt = self.naml.iberg_traj_tstamp
            if fmt == 'Timestep':
                # Timestep format time stamp
                if utils.calendar() == '360day' or freq[-1] in 'hd':
                    per_day = {'h': 1.0 / 24, 'd': 1, 'm': 30, 'y': 360}
                    freq = int(int(freq[:-1]) * per_day[freq[-1]])
                    delta = [0, 0, freq]
                    step = freq * self.naml.iberg_traj_ts_per_day
                    timestamp = '0'
                else:
                    utils.log_msg(
                        'Expected Iceberg Trajectory files can only be '
                        'determined with frequency {} when using the 360day '
                        'calendar.  Please use hours or days.'.format(freq),
                        level='FAIL'
                        )
            else:
                # YYYYMMDD-YYYYMMDD format time stamp
                delta = freq
                timestamp = ''

            while date < edate:
                newdate = utils.add_period_to_date(date, delta)
                if fmt == 'Timestep':
                    timestamp = str(int(timestamp) + step).zfill(6)
                else:
                    timestamp = '{}-{}'.format(
                        ''.join(str(x).zfill(2) for x in date[:3]),
                        ''.join(str(x).zfill(2) for x in newdate[:3])
                        )

                if newdate <= edate:
                    iceberg_traj[fileset].append(
                        filenames.FNAMES['nemo_ibergs_traj'].format(
                            P=self.prefix, TS=timestamp
                            )
                        )
                date = newdate

        return iceberg_traj

    def get_filename(self, period, start, end, stream):
        '''
        Return filename according to filenames.FNAMES regular expression.
        Arguments:
            period = mean period from the set [dmsyx]
            start = start date [year, month, day, hour]
            end = end date [year, month, day, hour]

        Inputs to filenames.FNAMES:
            CM = component model (netCDF convention only)
            P = filename prefix ($RUNID)
            R = model realm [aoil]
            F = data frequency
            CF = custom field (includes atmos stream ID)
            Y1, M1, D1 = start date
            Y2, M2, D2 = end date
        '''
        start = [str(x).zfill(2) for x in start]
        end = [str(x).zfill(2) for x in end]
        prefix = self.prefix

        if self.model == 'atmos' and re.match(r'^[pm][a-z1-9]$', stream):
            if 'h' in period:
                # Hourly files require "_HH" post-fix
                start[3] = '_{}'.format(start[3])
            else:
                start[3] = end[3] = ''

            m_streams = ['pm']
            if self.naml.streams_30d:
                m_streams += [str(s) for s in
                              utils.ensure_list(self.naml.streams_30d)]
            if stream in m_streams:
                start[2] = ''
                start[1] = MONTHS[int(start[1])]
            elif stream == 'ps':
                start[2] = ''
                for mth, ssn in self.seasons(self.meanref):
                    if int(start[1]) in range(mth, mth + 3):
                        start[1] = ssn
                        break
        else:
            if start[3] == end[3]:
                # Hour not required
                start[3] = end[3] = ''

            if self.model == 'atmos':
                stream = filenames.FIELD_REGEX

        key, realm, component = self.get_fn_components(stream)
        if key.startswith('ncf'):
            prefix = prefix.lower()
            if stream:
                stream = '_{}'.format(stream)

        return filenames.FNAMES[key].format(
            CM=component, P=prefix, R=realm, F=period, CF=stream,
            Y1=start[0], M1=start[1], D1=start[2], H1=start[3],
            Y2=end[0], M2=end[1], D2=end[2], H2=end[3]
            )
