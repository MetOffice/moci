#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    atmos.py

DESCRIPTION
    Atmosphere post processing application

ENVIRONMENT VARIABLES
  Standard Cylc environment:
    CYLC_SUITE_WORK_DIR
    CYLC_TASK_CYCLE_POINT
'''

import os
import re

from collections import OrderedDict

import control
import utils
import nlist
import validation
import housekeeping
import atmos_transform as transform
import suite
import climatemean
import timer

from netcdf_filenames import NCF_TEMPLATE

MONTHS = tuple(m[:3].lower() for m in climatemean.MONTHS)
SEASONS = tuple(''.join([c[0] for c in [MONTHS[m],
                                        MONTHS[(m + 1) % 12],
                                        MONTHS[(m + 2) % 12]]])
                for m in range(12))


class AtmosPostProc(control.RunPostProc):
    '''
    Methods and properties specific to the UM Atmosphere
    post processing application.
    '''
    def __init__(self, input_nl='atmospp.nl'):
        '''
        Initialise UM Atmosphere Postprocessing:
            Import namelists: atmospp, archiving, delete_sc
            Import required environment:
                CYLC_SUITE_WORK_DIR, CYLC_TASK_WORK_DIR
            Check WORK and SHARE directories exist
            Determine dumpname for final cycle: archived but not deleted
        '''
        self.naml = nlist.load_namelist(input_nl)
        self.convpp_streams = \
            self._stream_expr(self.naml.atmospp.archive_as_fieldsfiles,
                              inverse=True, default=['^a-z', '^1-9'])
        self.netcdf_streams = \
            self._stream_expr(self.naml.atmospp.streams_to_netcdf)
        self.cutout_streams = \
            self._stream_expr(self.naml.atmospp.streams_to_cutout)
        self.requested_means = self._requested_means()

        if self.runpp:
            self.share = self._directory(self.naml.atmospp.share_directory,
                                         'ATMOS SHARE')
            self.suite = suite.SuiteEnvironment(self.share, input_nl)
            self.work = self._directory(self._work, 'ATMOS WORK')

            if self.suite.finalcycle is True:
                self.final_dumpname = self.dumpname(
                    dumpdate=self.suite.cyclepoint.endcycle['intlist']
                    )
            else:
                self.final_dumpname = None

            # Initialise debug mode - calling base class method
            self._debug_mode(debug=self.naml.atmospp.debug)

    @property
    def runpp(self):
        '''
        Logical - Run postprocessing for UM Atmosphere
        Set via the atmospp namelist
        '''
        return self.naml.atmospp.pp_run

    @property
    def methods(self):
        '''
        Returns a dictionary of methods available for this model to the
        main program
        '''
        all_methods = self._process_methods
        all_methods.update(self._archive_methods)
        all_methods['finalcycle_complete'] = self.suite.finalcycle
        all_methods['finalise_debug'] = self.naml.atmospp.debug
        return all_methods

    @property
    def _process_methods(self):
        ''' Return <type OrderedDict> List of processing methods '''
        process_methods = OrderedDict()
        print(self.suite.naml.process_toplevel)
        if self.suite.naml.process_toplevel is True:
            process_methods['do_ozone'] = self.naml.atmospp.preserve_ozone
            process_methods['do_meaning'] = self.naml.atmospp.create_means
            process_methods['do_transform'] = (
                self.naml.atmospp.convert_pp or
                self.naml.atmospp.streams_to_netcdf
            )
        return process_methods
            
    @property
    def _archive_methods(self):
        ''' Return <type OrderedDict> List of archiving methods '''
        archive_methods = OrderedDict()
        if self.suite.naml.archive_toplevel is True:
            archive_methods['do_archive'] = self.naml.archiving.archive_switch
            archive_methods['do_delete'] = self.naml.delete_sc.del_switch
        return archive_methods

    @property
    def _work(self):
        ''' Work directory - Contains unprocessed .arch files'''
        cylc_work = utils.load_env('CYLC_SUITE_WORK_DIR', required=True)
        cylc_cycle = utils.load_env('CYLC_TASK_CYCLE_POINT', required=True)

        return os.path.join(cylc_work, cylc_cycle, self.suite.umtask)

    @property
    def streams(self):
        '''
        Returns a regular expression for the fieldsfile
        instantaneous streams to process'''
        requested_streams = self.naml.atmospp.process_streams
        if requested_streams:
            ozone_stream = self.naml.atmospp.ozone_output_stream
            if ozone_stream:
                requested_streams = utils.ensure_list(requested_streams)
                requested_streams.append(ozone_stream)

        return self._stream_expr(requested_streams,
                                 nullstring=True,
                                 default=['1-9', 'a-l', 'n-r', 't-x', 'z'])

    @property
    def means(self):
        'Returns a regular expression for the fieldsfile means to process'
        return self._stream_expr(self.naml.atmospp.process_means,
                                 nullstring=True, default=['m', 's', 'y'])

    @property
    def archive_tstamps(self):
        '''
        Return a list of timestamps for dumps to archive, having
        removed blank strings.
        '''
        tstamps = self.naml.archiving.arch_timestamps
        if not isinstance(tstamps, list):
            tstamps = [tstamps]
        return [ts for ts in tstamps if ts]

    def _requested_means(self):
        '''
        Return a dictionary of climatemean.MeanFiles with reference
        to the means requested in the namelist.
        '''
        if self.naml.atmospp.create_means:
            base_component = None
            if isinstance(self.naml.atmospp.meanbase_period, str):
                base_component = self.naml.atmospp.meanbase_period
            else:
                basestream = self.naml.atmospp.meanbase_stream
                for key in climatemean.MEANPERIODS:
                    if key[-1] == basestream[-1]:
                        base_component = key
                        break

            if base_component:
                self.naml.atmospp.base_component = base_component
            else:
                utils.log_msg('atmos requested means: cannot determine mean '
                              'base component reinitialisation period.  \n'
                              '\t Please set &atmospp/meanbase_period.',
                              level='ERROR')

        return climatemean.available_means(self.naml.atmospp)

    @property
    def netcdf_fields(self):
        '''
        Return a dictionary of field names or STASH codes
        with an associated descriptor.
        The namelist variable &atmospp.fields_to_netcdf
        should contain a list of pairs of <type str> such that
        len(fields) % 2 == 0:
            (field name or STASHcode, descriptor)

        The descriptor is to be used as the "custom" facet for the
        Met Office netCDF naming convention for netCDF diagnostic files.
        '''
        if self.netcdf_streams:
            fields = self.naml.atmospp.fields_to_netcdf
        else:
            fields = []

        if not isinstance(fields, list) or len(fields) % 2 != 0:
            msg = 'Incorrect format of &atmospp/fields_to_netcdf'
            msg += ' -> <field name>, <descriptor> pairs expected.'
            utils.log_msg(msg, level='WARN')
            fields = []

        return {key: fields[i+1] for i, key in enumerate(fields)
                if fields.index(key) % 2 == 0}

    def _stream_expr(self, streams,
                     inverse=False, nullstring=False, default=None):
        '''
        Return the regular expression required to find files
        which should be processed.
        Arguments:
           streams - <type list> or <type str> or <type NoneType>
        Optional Arguments:
           inverse    - <type bool>
                        Construct a regular expression for the inverse of
                        the incoming list of streams
           nullstring - <type bool>
                        Allow a return value of ''.  Otherwise, use default
           default    - Value to return if streams is None or an empty string
        '''
        if streams is None or (streams == '' and not nullstring):
            streams = default

        if streams:
            streams = utils.ensure_list(streams[:])
            if inverse != any(str(s).startswith('^') for s in streams):
                inv = ('?!', validation.VALID_STR)

            else:
                inv = ('', '')
            range_expr = '[{ID}]'
            for i, elem in enumerate(streams):
                idpm, id1, id2 = re.match(r'^\^?(\w?)(\w)-?(\w?)',
                                          str(elem)).groups()
                idpm = idpm if idpm else 'pm'
                elem = range_expr.format(ID=idpm)
                idstream = '-'.join([id1, id2]) if id2 else id1
                elem += range_expr.format(ID=idstream)
                streams[i] = elem

            streams = '({I}{S}){A}'.format(I=inv[0], S='|'.join(streams),
                                           A=inv[1])
        return streams

    def ff_match(self, stream_expr, filename=None, date_regex=None):
        '''
        Return a regular expression representing a fieldsfile filename.
        Arguments:
            stream_expr - Regular expression for required stream-ID(s)
        Optional Arguments:
            filename    - Where provided return the regular expression if the
                          given filename matches.  Otherwise return None
        '''
        try:
            prefix = self.suite.prefix
        except AttributeError:
            # Default to $RUNID
            prefix = utils.load_env('RUNID', required=True)

        if date_regex is None:
            # Regular expression to match UM output filename datestamp:
            #     "YYYYMMDD[_HH]" or "YYYYSSS"
            #  <match>.groups() = (<month,day,hour or season>, <hours>)
            #  <match>.group(1) not be present for ozone output (year only)
            #  <match>.group(2) only present for files reinitialised hourly
            date_regex = r'\d{4}(\d{4}|\w{3})?(_\d{2})?'

        ff_pattern = r'^{}a\.{}{}$'.format(prefix, str(stream_expr), date_regex)
        try:
            return re.match(ff_pattern, filename) is not None
        except TypeError:
            # Filename string not provided.  Return the pattern
            return ff_pattern

    def dumpname(self, dumpdate=None):
        '''
        Returns the dump name to be archived and/or deleted.
        Optional argument:
          dumpdate - List of <type int> values
                   - Default = current cyclepoint
        '''
        if dumpdate is None:
            dumpdate = self.suite.cyclepoint.startcycle['intlist']
        return '{0}a.da{1:0>4d}{2:0>2d}{3:0>2d}_{4:0>2d}'.\
            format(self.suite.prefix, *dumpdate)

    def dumps_to_archive(self, log_file):
        '''Returns a list of dump files to archive'''
        arch_dumps = []
        dump_files = validation.make_dump_name(self) if \
            self.naml.archiving.archive_dumps else []

        for fname in dump_files:
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                # Header verification required
                if validation.verify_header(
                        self.naml.atmospp, fnfull,
                        self.suite.envars['CYLC_TASK_LOG_ROOT'],
                        logfile=log_file
                    ):
                    arch_dumps.append(fname)
            else:
                # Dump file was probably archived by a previous instance
                # of the app at this cycle
                pass

        return arch_dumps

    @timer.run_timer
    def diags_to_process(self, finalcycle, log_file=None):
        '''
        Return a list of fields/pp files eligible to file transformation
        or archive.
        Filenames returned will always include full path.
        '''
        datadir = self.share if finalcycle else self.work
        suffix = r'(\.pp)?' if finalcycle else '.arch'

        markedfiles = []
        if self.streams:
            # Get instantaneous pp/fieldsfiles to be processed
            patt = self.ff_match(self.streams)
            markedfiles += housekeeping.get_marked_files(datadir, patt, suffix)
        if self.means:
            # Get mean pp/fieldsfiles to be processed
            patt = self.ff_match(self.means)
            markedfiles += housekeeping.get_marked_files(datadir, patt, suffix)

        process_files = []
        for fname in markedfiles:
            fnfull = os.path.join(self.share, fname)
            if os.path.exists(fnfull):
                if fnfull.endswith('.pp'):
                    # Header verifcation already complete
                    process_files.append(fnfull)
                elif validation.verify_header(
                        self.naml.atmospp, fnfull,
                        self.suite.envars['CYLC_TASK_LOG_ROOT'],
                        logfile=log_file
                    ):
                    # Header verification required
                    process_files.append(fnfull)
            elif os.path.exists(fnfull + '.pp'):
                # Collect any previously converted ppfiles
                process_files.append(fnfull + '.pp')
            else:
                msg = 'File for processing {} does not exist'.format(fnfull)
                utils.log_msg(msg, level='WARN')

        if self.naml.archiving.archive_ncf:
            # Collect any previously created netCDF files for archiving
            ncfiles = utils.get_subset(
                self.share,
                NCF_TEMPLATE.format(P='atmos_{}a'.format(self.suite.prefix),
                                    B=r'\d+[hdmsyx]',
                                    S=r'\d{8}(\d{2})?',
                                    E=r'\d{8}(\d{2})?',
                                    C='.*') + '$'
            )
            process_files += [os.path.join(self.share, fn) for fn in ncfiles]

        return process_files

    @timer.run_timer
    def update_meanfile(self, meanfile, setend_fname):
        '''
        Update the periodend, component files and mean filename attributes
        of the meanfile input object before calling Mule to create the
        relevant mean file.
        Arguments:
            meanfile <type climatemean.MeanFile>
            setend_fname <type str> - Filename, excluding path, of the
                                      end-of-set component
        '''
        key0_id = list(self.requested_means.keys())[0]
        if meanfile == self.requested_means[key0_id]:
            basestream = self._stream_expr(self.naml.atmospp.meanbase_stream)
        else:
            basestream = 'p' + meanfile.component[-1]

        # Calculate the end date of the mean period
        setend_filedate = validation.identify_dates(setend_fname)[0]

        meanfile.periodend = setend_filedate[:]
        if meanfile.component[-1] in 'hdms':
            # Update periodend where end-of-set regex does not represent the
            # END date of the file.
            meanfile.periodend = climatemean.calc_enddate(setend_filedate,
                                                          meanfile.component)

        # Get the component files for the mean
        setdate = climatemean.set_date_regex(
            meanfile.period, meanfile.component, meanfile.periodend,
            rtnend=(meanfile.component[-1] in 'yx')
            )
        setregex = []
        for date in validation.identify_dates(setdate):
            setregex.append(validation.get_filedate(date, meanfile.component))
        regex = '({})'.format('|'.join([''.join(d) for d in setregex]))
        modyr = re.search(r'(\d{4})(ndj|djf)', regex)
        if modyr:
            # for the seasonal mean: update the year to end of period
            regex = regex.replace(
                ''.join(modyr.groups()),
                ''.join([str(int(modyr.group(1)) + 1), modyr.group(2)])
                )

        setpatt = self.ff_match(basestream, date_regex=regex)
        # Allow for components already converted to pp format
        setpatt = setpatt.replace('$', r'(\.pp)?$')
        meanfile.component_files = utils.add_path(
            utils.get_subset(self.share, setpatt), self.share
            )

        filedate = validation.get_filedate(
            meanfile.periodend, meanfile.period,
            end_of_period=(meanfile.period[-1] in 'ms')
            )
        meanfile.set_filename('{}a.p{}{}'.format(self.suite.prefix,
                                                 meanfile.period[-1],
                                                 ''.join(filedate)),
                              self.share)

        # Create the mean file
        if meanfile.fname['file'] == setend_fname:
            utils.log_msg('The requested mean is a direct UM output: ' +
                          setend_fname, level='INFO')
            rcode = 1
        elif os.path.isfile(meanfile.fname['full'] + '.pp'):
            # Failure recovery - file already exists in pp format
            # climatemean.create_mean() will pick up pre-existing fieldsfile.
            utils.log_msg('The requested mean file already exists in '
                          'pp format: ' + meanfile.fname['file'],
                          level='INFO')
            rcode = 0
        elif any([f.endswith('.pp') for f in meanfile.component_files]):
            # Failure recovery - on or more of the components is already in
            # pp format - this may happen if a previous task failed having
            # successfully created the mean and then converted the components.
            # The mean file itself may already be in the archive.
            utils.log_msg('Component(s) of the requested mean file are already '
                          'in pp format:\n\t' + \
                              '\n\t'.join(meanfile.component_files),
                          level='WARN')
            utils.log_msg('Continuing. {} is '.format(meanfile.fname['file']) +
                          'assumed to have been created successfully.',
                          level='WARN')
            rcode = 0
        else:
            rcode = climatemean.create_mean(meanfile,
                                            transform.create_um_mean,
                                            self.suite.initpoint)

        return rcode

    @timer.run_timer
    def do_meaning(self):
        '''
        Perform the creation of climate means as requested.
        '''
        if int(self.suite.meanref[2]) > 1:
            utils.log_msg('Creation of UM Atmosphere means requires a '
                          '&suitegen/mean_reference_date with the 1st of the '
                          'month. Means cannot be created.', level='WARN')
            return

        flagdir = os.path.join(self.share, 'mean_archflags')
        utils.create_dir(flagdir)

        basestream = self._stream_expr(self.naml.atmospp.meanbase_stream)

        match_base = self.ff_match(basestream)
        # Save any archiving flags for base component file
        markedfiles = housekeeping.get_marked_files(self.work, match_base,
                                                    '.arch')
        # Ensure that components are still in fieldsfile format
        archflags = []
        for archflag in markedfiles:
            if os.path.isfile(os.path.join(self.share, archflag)):
                archflags.append(archflag + '.arch')
        if len(archflags) == len(markedfiles):
            utils.move_files(archflags, flagdir,
                             originpath=self.work)

        # Loop over requested mean periods
        for meanp in self.requested_means:
            meanfile = self.requested_means[meanp]
            match_end = climatemean.end_date_regex(meanp, self.suite.meanref)
            end_filedates = validation.get_filedate(match_end,
                                                    meanfile.component,
                                                    end_of_period=True)
            endpatt = self.ff_match(basestream, date_regex=end_filedates)
            for setend in housekeeping.get_marked_files(flagdir, endpatt,
                                                        '.arch'):
                # Attempt to create mean with `setend` as the end-of-period file
                icode = self.update_meanfile(meanfile, setend)
                if icode == 0:
                    if meanp == list(self.requested_means.keys())[-1]:
                        flag_destination = self.work
                    else:
                        flag_destination = flagdir
                    # Touch archiving flag for the new meanfile
                    open(os.path.join(flag_destination,
                                      meanfile.fname['file'] + '.arch'),
                         'w').close()

                    # Return component archiving flags to the work directory
                    for cmpt in meanfile.component_files:
                        # Strip path and any .pp file extension from .arch name
                        cmpt = re.sub('.pp$', '', os.path.basename(cmpt))
                        arch = os.path.join(flagdir, cmpt + '.arch')
                        if os.path.exists(arch):
                            utils.move_files(arch, self.work)

            if self.suite.finalcycle:
                # Check for base components not yet reinitialised
                for setend in housekeeping.get_marked_files(self.share, endpatt,
                                                            ''):
                    _ = self.update_meanfile(meanfile, setend)

            basestream = 'p' + meanfile.period[-1]

    @timer.run_timer
    def do_ozone(self):
        '''
        Process density and tropopause height data for later use in
        ozone redistribution.
        FIELDSFILES on disk required.
        '''
        source_stream = str(self.naml.atmospp.ozone_source_stream)
        if len(source_stream) < 2:
            source_stream = 'p' + source_stream
        output_stream = self.naml.atmospp.ozone_output_stream

        if output_stream:
            if len(output_stream) < 2:
                output_stream = 'p' + output_stream
            # Make sure there aren't any arch flags produced by the UM
            archflags = housekeeping.get_marked_files(
                self.work, self.ff_match(output_stream), '.arch'
            )
            for flag in archflags:
                # Test for potential conflict with UM output - there should be
                # no recent files marked for processing
                try:
                    year = re.match(
                        # Regular expression to UM output filename:
                        #     "<RUNID>a.<STREAM ID><YEAR>"
                        #  <match>.group(1) = Filename datestamp year
                        r'^.*a.{}(\d{{4}})'.format(validation.VALID_STR), flag
                    ).group(1)
                except AttributeError:
                    year = 0
                if int(year) >= \
                   self.suite.cyclepoint.startcycle['intlist'][0] - 1:
                    # Potential conflict between UM output and new file
                    utils.log_msg(
                        'do_ozone - Requested output stream for ozone '
                        'redistribution appears to match existing UM output',
                        level='FAIL'
                    )

            fields = utils.ensure_list(self.naml.atmospp.ozone_fields)
            source_files = housekeeping.get_marked_files(
                self.share, self.ff_match(source_stream), '')

            utils.log_msg(
                'Attempting to extract ozone fields {} from\n\t{}'.
                format(fields, '\n\t'.join(source_files))
                )
            # Assume data frequency for ozone fields is always 1m
            icode = transform.extract_to_pp(
                [os.path.join(self.share, s) for s in source_files],
                fields, output_stream, data_freq='1m'
                )
            if icode == 0:
                utils.log_msg('Successfully extracted ozone fields')
            else:
                # Fail immediately - we don't want source file(s)
                # subsequently processed and archived
                utils.log_msg('Failed extracting ozone fields',
                              level='FAIL')

            output_files = housekeeping.get_marked_files(
                self.share, self.ff_match(output_stream), ''
            )
        else:
            # Input to ozone redistribution is direct UM output.
            # Collect .arch flags for source files
            archflags = housekeeping.get_marked_files(
                self.work,
                self.ff_match(source_stream),
                '.arch'
            )
            utils.remove_files([f + '.arch' for f in archflags],
                               path=self.work)

            # Convert any source files available to pp format
            output_files = housekeeping.get_marked_files(
                self.share, self.ff_match(source_stream), ''
            )
            for sfile in output_files:
                rmff = sfile in archflags
                sfile = utils.add_path(sfile, self.share)[0]
                if utils.compare_mod_times([sfile, sfile + '.pp']) == sfile:
                    transform.convert_to_pp(sfile,
                                            self.naml.atmospp.um_utils,
                                            self.naml.atmospp.mule_utils,
                                            not rmff)
                elif rmff:
                    utils.remove_files(sfile, ignore_non_exist=True)

        for ofile in output_files:
            year = re.match(r'^.*a.{}(\d{{4}})'.format(validation.VALID_STR),
                            ofile).group(1)
            if int(year) < self.suite.cyclepoint.startcycle['intlist'][0] - 1:
                # Create .arch file for file older than 2 years
                open(os.path.join(self.work, ofile + '.arch'), 'w').close()

    @timer.run_timer
    def do_transform(self, finalcycle=False):
        '''
        Function to perform requested transformation of fieldsfiles.
        '''
        # Get files which are available to archive, and thus eligible
        # for transform operations.
        for fname in self.diags_to_process(finalcycle):
            # fname returned by diags_to_process always includes the full path
            basename = os.path.basename(fname)

            if not fname.endswith('.pp'):
                if self.ff_match(self.cutout_streams, filename=basename):
                    _ = transform.cutout_subdomain(
                        fname,
                        self.naml.atmospp.mule_utils,
                        self.naml.atmospp.cutout_coords_type,
                        self.naml.atmospp.cutout_coords
                        )

                if self.naml.atmospp.convert_pp:
                    if self.ff_match(self.convpp_streams, filename=basename):
                        fname = transform.convert_to_pp(
                            fname,
                            self.naml.atmospp.um_utils,
                            self.naml.atmospp.mule_utils,
                            finalcycle is True
                            )

            # Ensure previously created pp files are picked up from here on
            if basename.endswith('.pp'):
                basename = basename[:-3]

            if self.ff_match(self.netcdf_streams, basename):
                icode = transform.extract_to_netcdf(
                    fname, self.netcdf_fields,
                    self.naml.atmospp.netcdf_filetype,
                    self.naml.atmospp.netcdf_compression
                    )
                if icode != 0:
                    msg = 'do_transform - Field extraction to netCDF failed'
                    utils.log_msg(msg, level='ERROR')

    @timer.run_timer
    def do_archive(self, finalcycle=False):
        '''
        Function to collate the files to archive and pass them to the
        archiving script.
        Optional argument: finalcycle=True when called from finalcycle_complete.
        '''
        # Open our log files
        action = 'a' if os.path.exists(self.suite.logfile) else 'w'
        try:
            log_file = open(self.suite.logfile, action)
        except IOError:
            utils.log_msg('Failed to open archive log file', level='FAIL')

        # Get files to archive
        files_to_archive = []
        if self.naml.archiving.archive_pp:
            files_to_archive += self.diags_to_process(finalcycle,
                                                      log_file=log_file)
            # Do not archive both fieldsfile and ppfile
            files_to_archive = [fn for fn in files_to_archive
                                if fn + '.pp' not in files_to_archive]
        if not finalcycle:
            # Dumps are archived by first call to do_archive during final cycle
            files_to_archive += self.dumps_to_archive(log_file)

        log_file.close()

        # Perform the archiving
        if files_to_archive:
            msg = 'Archiving the following files:\n'
            msg += '\n '.join(files_to_archive)
            utils.log_msg(msg)

            for fname in files_to_archive:
                fname_only = os.path.basename(fname)
                if fname_only.endswith('.pp'):
                    fname_only = fname_only[:-3]
                # convpp should be True when the ffile is to be archived as pp
                convpp = (
                    self.ff_match(self.convpp_streams, filename=fname_only)
                    or not self.naml.atmospp.convert_pp
                    )
                rcode = self.suite.archive_file(fname, preproc=bool(convpp))
                if finalcycle and rcode == 0 and fname[-3:] in ['.pp', '.nc']:
                    if utils.get_debugmode():
                        os.rename(fname, fname + '_ARCHIVED')
                    else:
                        utils.remove_files(fname)

        else:
            utils.log_msg(' -> Nothing to archive')

    @timer.run_timer
    def finalcycle_complete(self):
        '''
        Archive but do not delete potentially incomplete fieldsfiles left
        on disk at the completion of the final cycle.
        '''
        if self.suite.naml.process_toplevel:
            if self.naml.atmospp.convert_pp or self.netcdf_streams:
                self.do_transform(finalcycle=True)

        if self.suite.naml.archive_toplevel:
            if self.naml.archiving.archive_switch:
                self.do_archive(finalcycle=True)

    @timer.run_timer
    def do_delete(self):
        '''Delete superseded or archived dumps and pp output'''
        archived = self.naml.archiving.archive_switch
        dump = pp_inst = pp_mean = ncfile = None

        if archived:
            dump, pp_inst, pp_mean, ncfile = \
                housekeeping.read_arch_logfile(self.suite.logfile,
                                               self.suite.prefix,
                                               self.streams,
                                               self.means,
                                               self.netcdf_streams)

        housekeeping.delete_dumps(self, dump, archived)
        housekeeping.delete_ppfiles(self, pp_inst, pp_mean, ncfile,
                                    archived)


INSTANCE = ('atmospp.nl', AtmosPostProc)

if __name__ == '__main__':
    pass
