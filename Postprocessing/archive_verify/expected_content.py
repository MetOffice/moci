#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2025 Met Office. All rights reserved.

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
import os

import filenames
import utils
import climatemean

MONTHS = tuple(m[:3].lower() for m in climatemean.MONTHS)
SEASONS = tuple(''.join([c[0] for c in [MONTHS[m],
                                        MONTHS[(m + 1) % 12],
                                        MONTHS[(m + 2) % 12]]])
                for m in range(12))


def season_starts(ref_month):
    '''
    Return a list of start months for seasons give a mean reference month
    '''
    start_months = [mth % 12 for mth in
                    range(int(ref_month), int(ref_month) + 12, 3)]
    if 0 in start_months:
        start_months[start_months.index(0)] = 12

    return sorted(start_months)


class ClimateMean(object):
    '''
    Object to represent a climate mean period.
    Arguments:
        period:      Climate mean period - one of climatemean.MEANPERIODS
        next_period: Subsequent period (if any), for which files of this period
                   may need to remain on disk as components.
        component:   <type dict> keys: base_cmpt, base_buff (opt), fileid (opt)
                        base_cmpt: <type str>  period of the base component
                        base_buff: <type int> No. of base components retained
                                 in a file buffer or not yet reinitialised
                        fileid:    <type str>  Required when the filename may
                                 not be discerned from the period (atmos only)
    '''
    def __init__(self, period, next_period, component):
        self.period = period
        self.next = next_period
        self.previous = component['base_cmpt']
        self.component_stream = component.get('fileid', None)
        self.component_buffer = component.get('base_buff', 0)

    def get_availability(self, file_enddate, meanref):
        '''
        Return <type bool>: True if a mean file should be available in the
                           archive; dependent on the necessity to keep files
                           on disk as components of future higher means
                           (self.next).
        Arguments:
            file_end_date <type list> of <type int>
                          [YY,MM,DD] End date of the period file
            meanref       <type list> of <type int>
                          [YY,MM,DD] Mean reference date
        '''
        # 10day mean only relevant for 360d calendar - use range(1,31)
        days10 = list(range(meanref[2], 31, 10))
        if len(days10) < 3:
            days10.append(meanref[2] - 10)
        conditions = {
            '10d': (file_enddate[2] in days10,),
            '1m': (file_enddate[2] == meanref[2],),
            '1s': (file_enddate[1] in season_starts(meanref[1]),
                   file_enddate[2] == meanref[2]),
            '1y': (file_enddate[1] == meanref[1],
                   file_enddate[2] == meanref[2]),
            '1x': (str(file_enddate[0])[-1] == str(meanref[0])[-1],
                   file_enddate[1] == meanref[1],
                   file_enddate[2] == meanref[2])
            }

        return all(conditions.get(self.next, []))


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
    Namelist variables containing stream identifier values will follow
    the naming convention:
      * streams_<period>     - e.g. streams_10d
      * <function>_stream[s] - e.g. ff_streams, ozone_stream

    Atmosphere stream IDs should be two character.
    Format = [pm][a-z0-9]
    Single character namelist input is accepted, in which case the
    first character is assumed to be "p".

    Return the namelist with all streams variables containing
    a list of 2 character values.

    Arguments:
       naml - <type utils.Variables> Namelist object
    '''
    stream_namelists = [a for a in dir(naml)
                        if a.startswith('streams_')
                        or re.match(r'^.*_streams?$', a)]

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
        Arguments:
            filename - <type str> Filename to contain a date of the form:
                                  YY[yy]MMDD[[_]HH]
                                  YYYY<3char month/ssn>
                                  YYYY-MM-DD[-HH]
        Optional Arguments:
            start - <type bool> When True return start date, otherwise end
        '''

        date_patterns = (r'\d{4}[a-z]{3}', r'\d{8}_\d{2}', r'\d{6,10}',
                         r'\d{4}-\d{2}-\d{2}-\d{2}?-?')
        for patt in date_patterns:
            dates = re.findall(patt, filename)
            if dates:
                break

        split = r'(\d{4})-?(\d{2}|[a-z]{3})-?(\d{2})?-?(\d{2})?-?_?(\d{2})?'
        date_lists = [re.match(split, d).groups() for d in dates]
        date = list(date_lists[0 if start else -1])
        date[0] = int(date[0])
        try:
            date[1] = int(date[1])
        except ValueError:
            # Special case for atmosphere monthly and seasonal files
            try:
                # Monthly files
                date[1] = range(1, 13)[MONTHS.index(date[1]) - 1]
                if not start:
                    date[1] = range(1, 13)[date[1] % 12]
                    date[0] += (date[1] == 1)
            except ValueError:
                # Seasonal files
                date[1] = range(1, 13)[SEASONS.index(date[1]) - 1]
                if start:
                    date[0] -= (date[1] > 9)
                else:
                    date[1] = range(1, 13)[(date[1] + 2) % 12]
                    date[0] += (date[1] == 1)

        date[2] = int(date[2]) if date[2] else 1
        date[3:] = [int(x) for x in date[3:] if x]

        return date

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
            # "component" is relevant to the netCDF convention filenames
            # and UniCiCles diagnostics
            if component == 'bisicles':
                key = 'bisicles_diag_hdf'
            elif component == 'unicicles':
                key = 'unicicles_diag_ncf'
            else:
                # A netCDF convention filename
                key = 'ncf_mean'
        elif (stream).endswith('_rst'):
            # Restart files
            key = 'rst'
        else:
            # Atmosphere fields/pp files
            ozone_stream = self.naml.ozone_stream
            if isinstance(ozone_stream, list) and len(ozone_stream) > 0:
                ozone_stream = ozone_stream[0]
            if str(stream) == ozone_stream:
                try:
                    ozone_1y = str(stream) in self.naml.streams_1y
                except AttributeError:
                    ozone_1y = False
                key = 'atmos_ozone' if ozone_1y else 'atmos_pp'
            elif str(stream) in self.naml.ff_streams:
                key = 'atmos_ff'
            else:
                key = 'atmos_pp'

        return key, realm, component


class RestartFiles(ArchivedFiles):
    '''
    Methods specific to determining restart filenames expected to be present
    in the archive.

    Required environment: CYCLEPERIOD - ISO format period, e.g. "P1M"
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
        if model == 'unicicles':
            # UniCiCles can be run without Greenland or Antarctica ice sheets,
            # so there are no restart files which are used everytime that
            # UniCiCles is run. Hence, there is no restart file which could be
            # 'unicicles_rst'.
            self.rst_types = []
        else:
            self.rst_types = ['{}_rst'.format(model)]
        for rst in [a for a in dir(naml) if a.endswith('_rst')]:
            if getattr(self.naml, rst):
                self.rst_types.append(rst)

    def _timestamps(self):
        ''' Return a list of timestamps '''
        meanref = nlist_date(self.naml.mean_reference_date,
                             'mean reference date')
        seasons = season_starts(meanref[1])
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
        for year in range(self.sdate[0], self.edate[0] + 1):
            for tstamp in self.timestamps:
                for rsttype in self.rst_types:
                    coll = self.get_collection(stream=rsttype)
                    newfile = self.get_filename(year, tstamp[0], tstamp[1],
                                                suffix, rsttype)
                    try:
                        restart_files[coll].append(newfile)
                    except KeyError:
                        restart_files[coll] = [newfile]

        for rstcoll in restart_files:
            restart_files[rstcoll] = self.remove_invalid(restart_files[rstcoll])

        if self.finalcycle and not coll.startswith('c'):
            # Additionally archive the end date dump.
            # Ignore UniCiCles because it does not necessarily
            # run on the final cycle.
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

        for key in list(restart_files.keys()):
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
            try:
                cyclefreq = self.naml.cycle_length
            except AttributeError:
                cyclefreq = os.environ.get('CYCLEPERIOD', None)
            rst_buffer = self.naml.buffer_restart

            if isinstance(cyclefreq, str):
                cyclefreq = '-' + cyclefreq
            else:
                # Check whether `isodatetime` command exists,
                # or default to `rose date`
                if utils.get_utility_avail('isodatetime'):
                    datecmd = 'isodatetime'
                else:
                    datecmd = 'rose date'

                cycletime = utils.CylcCycle().startcycle['iso']
                edate_str = [str(x).zfill(2) for x in edate]
                while len(edate_str) < 5:
                    edate_str.append('00')
                endtime = '{}{}{}T{}{}Z'.format(*edate_str[:5])
                cmd = '{} {} {} --calendar {}'.format(
                    datecmd, endtime, cycletime, utils.calendar()
                    )
                rcode, cyclefreq = utils.exec_subproc(cmd, verbose=False)
                if rcode != 0:
                    utils.log_msg('restart buffer - unable to calculate cycling'
                                  ' period. Reverting to buffer_restart=1',
                                  level='WARN')
                    rst_buffer = 1

            while isinstance(rst_buffer, int) and rst_buffer > 1:
                edate = utils.add_period_to_date(edate, cyclefreq)
                rst_buffer -= 1

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
        Yield <type tuple>:
           base     - period of the data in the stream
           delta    - reinitialisation period of the stream
           streams  - list of stream ids to process
           descript - "[concatenated_]mean" or "instantaneous" stream
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
                descript = 'mean' if base == delta else 'concatenated_mean'
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
            while sdate[1] not in season_starts(self.meanref[1]):
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

    def expected_means(self):
        '''
        Return <type tuple> :
           ( <type dict> : {period: <type CLimateMean>} -
                  Dictionary of ClimateMeans,
             <type ClimateMean> -
                   A pseudo-ClimateMean representing the base component )

        The base component representation is <type None> if the base component
        is a member of the requested means
        '''
        meanperiods = utils.ensure_list(self.naml.meanstreams)
        if not meanperiods:
            # No means requested.  Turn off climate mean verification
            self.naml.pp_climatemeans = False

        base_cm = None
        if self.naml.pp_climatemeans:
            mean_streams = self.climate_meanfiles(meanperiods)
            period1 = mean_streams[meanperiods[0]]
            if period1.previous not in meanperiods:
                component = {'base_cmpt': period1.previous,
                             'base_buff': period1.component_buffer,
                             'fileid': period1.component_stream}
                if period1.component_stream:
                    component['fileid'] = period1.component_stream
                else:
                    component['fileid'] = '|'.join(self.meanfields)

                base_cm = ClimateMean(period1.previous, period1.period,
                                      component)
        else:
            mean_streams = {k: None for k in meanperiods}

        return mean_streams, base_cm

    def expected_diags(self):
        ''' Generate a list of expected diagnostic output files '''
        all_files = {}
        intermittent_coll = {}

        all_streams = [a for a in dir(self.naml) if a.startswith('streams')]

        mean_streams, base_cm = self.expected_means()
        all_streams += mean_streams.keys()

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

        try:
            ozone_stream = self.naml.ozone_stream
        except AttributeError:
            ozone_stream = None
        if isinstance(ozone_stream, list) and len(ozone_stream) > 0:
            ozone_stream = ozone_stream[0]
            try:
                umoutput = ozone_stream in self.naml.streams_1m
            except TypeError:
                # Default namelist value: streams_1m=None
                umoutput = False
            if not umoutput:
                # Additional 1y stream, archived with a delay of 2 years
                try:
                    self.naml.streams_1y.append(ozone_stream)
                except AttributeError:
                    self.naml.streams_1y = [ozone_stream]
                    all_streams.append('streams_1y')

        for base, delta, streams, descript in \
                self.gen_reinit_period(list(set(all_streams))):
            date = self.get_period_startdate(delta[-1])
            edate = self.edate[:]
            while len(edate) < 5:
                edate.append(0)

            if not self.finalcycle:
                if base_cm is None:
                    try:
                        file_buffer = self.naml.buffer_mean
                    except AttributeError:
                        file_buffer = 0
                else:
                    file_buffer = base_cm.component_buffer

                if self.naml.pp_climatemeans:
                    cm_edate = edate[:]
                    try:
                        # Base component is not in the requested mean periods
                        base_period = base_cm.period
                    except AttributeError:
                        base_period = [p for p, m in mean_streams.items()
                                       if m.previous == m.period][0]

                    while file_buffer > 0:
                        cm_edate = utils.add_period_to_date(
                            cm_edate, '-' + base_period
                            )
                        file_buffer -= 1

                    deltamean = mean_streams.get(delta, base_cm)
                    try:
                        while not deltamean.get_availability(cm_edate,
                                                             self.meanref):
                            cm_edate = utils.add_period_to_date(cm_edate, '-1d')
                    except AttributeError:
                        # delta is neither a mean period nor a base component
                        pass

                    if descript == 'mean':
                        edate = cm_edate[:]

                while file_buffer > 0:
                    edate = utils.add_period_to_date(edate, '-' + delta)
                    file_buffer -= 1

            while date <= edate:
                newdate = utils.add_period_to_date(date, delta)

                if self.model == 'atmos' and descript == 'instantaneous':
                    # Due to reinitialisation method, Atmos instantaneous
                    # streams are created at the start of the period, and
                    # are not available at the edate.
                    add_file = (date if self.finalcycle else newdate) < edate
                else:
                    # Files are created at the end of the period
                    add_file = newdate <= edate

                if add_file:
                    if self.model == 'atmos' and descript == 'mean':
                        # Adjust year for atmosphere means - use end year
                        if newdate[1:3] > [1, 1] or delta not in '1m1s':
                            date[0] = newdate[0]

                    for stream in streams:
                        stream = str(stream)
                        if not self.finalcycle and descript == 'instantaneous' \
                           and base_cm and stream in base_cm.component_stream \
                           and date >= cm_edate:
                            # Base component stream - awaiting higher mean
                            continue

                        if stream == ozone_stream and base == '1y' and \
                           date >= utils.add_period_to_date(edate, '-1y11m'):
                            # 2 year archiving delay for PostProc produced
                            # ozone output
                            continue

                        if stream in self.tlim and \
                                (date < self.tlim[stream][0] or
                                 date > self.tlim[stream][1]):
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
            if fileset in intermittent_coll:
                pattern = intermittent_patterns[
                    intermittent_streams.index(intermittent_coll[fileset])
                    ]
                for i, fname in enumerate(all_files[fileset][:]):
                    if pattern[i % len(pattern)] == 'x':
                        all_files[fileset].remove(fname)

        all_files.update(self.iceberg_trajectory())

        for key in list(all_files.keys()):
            # Call to keys() required since we are removing dictionary keys
            if all_files[key] == []:
                del all_files[key]

        return all_files

    def climate_meanfiles(self, meanperiods):
        '''
        Return a <type dict> where:
            keys   = Climate mean period - one of climatemean.MEANPERIODS
            values = <type ClimateMean> object
        Arguments:
            meanperiods - Single or list of mean periods to be verified
                          (from climatemean.MEANPERIODS)
        '''
        meanperiods = utils.ensure_list(meanperiods)
        component = re.match(r'^(\d+|[pm])?([a-z0-9])$',
                             self.naml.base_mean).groups()

        try:
            file_buffer = self.naml.buffer_mean
        except AttributeError:
            file_buffer = 0

        if str(component[0]).isdigit():
            component = self.naml.base_mean
            component_id = None
        else:
            # Establish the period of the base mean, where the base_mean is
            # a stream ID rather than a period (Atmosphere)
            if component[0] is None:
                component_id = 'p' + component[0]
            else:
                component_id = ''.join(component)
            if component_id.replace('p', '1') in meanperiods:
                component = component_id.replace('p', '1')
            else:
                reinit_streams = [a for a in dir(self.naml)
                                  if re.match(r'streams_\d+[hdmsyx]', a)]
                while isinstance(component, tuple):
                    try:
                        reinit = reinit_streams.pop()
                        try:
                            if component_id in getattr(self.naml, reinit):
                                component = reinit.split('_')[-1]
                                file_buffer += 1
                        except TypeError:
                            # reinit namelist is None
                            pass
                    except IndexError:
                        utils.log_msg('Unable to calculate the period of the '
                                      'base component of the first mean.  '
                                      'Please adjust &atmosverify/base_mean',
                                      level='ERROR')
                        component = '1m'

        meanfiles = {}
        for i, m_period in enumerate(meanperiods[:]):
            try:
                next_period = meanperiods[i+1]
            except IndexError:
                next_period = None

            m_component = {'base_cmpt': component,
                           'base_buff': file_buffer}
            try:
                m_component['fileid'] = component_id
            except NameError:
                pass
            meanfiles[m_period] = ClimateMean(m_period, next_period,
                                              m_component)
            # Update component for next period
            component = m_period

            if component_id:
                component_id = m_period.replace('1', 'p')

        return meanfiles

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
                m_streams += [str(s) for s in self.naml.streams_30d]
            if self.naml.streams_1m:
                m_streams += [str(s) for s in self.naml.streams_1m]
            # Gregorian calendar 3m streams use the first month in filename
            if utils.calendar().lower() == 'gregorian' and self.naml.streams_3m:
                m_streams += [str(s) for s in self.naml.streams_3m]

            if stream in m_streams:
                start[2] = ''
                start[1] = MONTHS[int(start[1]) % 12]
            elif stream == 'ps':
                start[2] = ''
                start[1] = SEASONS[int(start[1]) % 12]
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
