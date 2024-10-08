#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2024 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    nemo.py

DESCRIPTION
    Class definition for NemoPostProc - holds NEMO model properties
    and methods
'''
import os
import re
import shutil

import timer
import utils
import modeltemplate as mt
import netcdf_filenames
import netcdf_utils

THICKNESS_WEIGHTED_VARIABLES = [
    'votemper', 'vosaline', 'vozocrtx', 'vomecrty',
    'votemper2', 'vosaline2', 'vozocrtx2', 'vomecrty2',
    'ut', 'us', 'urhop', 'vt', 'vs', 'vrhop',
    'ttrd_xad', 'strd_xad', 'ttrd_yad', 'strd_yad', 'ttrd_zad', 'strd_zad',
    'ttrd_ad', 'strd_ad', 'ttrd_totad', 'strd_totad', 'ttrd_ldf', 'strd_ldf',
    'ttrd_iso_x', 'strd_iso_x', 'ttrd_iso_y', 'strd_iso_y', 'ttrd_iso_z1',
    'strd_iso_z1',
    'ttrd_iso_z', 'strd_iso_z', 'ttrd_iso', 'strd_iso', 'ttrd_zdf', 'strd_zdf',
    'ttrd_evd', 'strd_evd', 'ttrd_zdfp', 'strd_zdfp', 'ttrd_dmp', 'strd_dmp',
    'ttrd_bbl', 'strd_bbl', 'ttrd_npc', 'strd_npc', 'ttrd_qsr', 'ttrd_bbc',
    'ttrd_atf', 'strd_atf', 'ttrd_tot', 'strd_tot',
    'thetao', 'so', 'uo', 'u2o', 'uto', 'uso', 'vo', 'vto', 'vso', 'v2o']
VOLUME_WEIGHTED_VARIABLES = ['temptot', 'saltot']
THICK_WEIGHT_CELL_METHODS = 'time: mean (thickness weighted)'
VOL_WEIGHT_CELL_METHODS = 'time: mean (volume weighted)'


class NemoPostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the NEMO post processing application.
    '''
    def __init__(self, input_nl='nemocicepp.nl'):
        super(NemoPostProc, self).__init__(input_nl=input_nl)
        self.region_fields = self._region_fields
        self.inst_fields += self.region_fields

    @property
    def _mean_fields(self):
        ''' Return the means fieldsfile types to be processed '''
        fields = []
        if self.naml.processing.means_fieldsfiles:
            fields += utils.ensure_list(self.naml.processing.means_fieldsfiles)
        else:
            for val in self.model_components.values():
                fields += [f for f in val if 'shelf' not in f]
        return sorted(fields)

    @property
    def _region_fields(self):
        ''' Return the fieldsfile types to be converted to regional files '''
        fields = []
        if self.naml.processing.extract_region:
            if isinstance(self.naml.processing.region_fieldsfiles, (str, list)):
                fields += utils.ensure_list(
                    self.naml.processing.region_fieldsfiles
                    )
            else:
                for val in self.model_components.values():
                    fields += [f for f in val if 'shelf' in f]
        return fields

    @property
    def rsttypes(self):
        '''
        Restart file types.
        Tuple( Filetype tag immediately following "RUNIDo_" in filename,
               Filetype tag immediately following "restart" in filename )
	       "icebergs" covers iceberg restarts pre NEMO 4.2
	       "icb" covers iceberg restarts post NEMO 4.2
        '''
        return (('', ''), ('', '_ice'), ('icebergs', ''), ('', '_icb'), ('', '_trc'))

    @property
    def model_components(self):
        '''Name of model component, to be used as a prefix to archived files '''
        return {
            'nemo': ['grid_T', 'grid_U', 'grid_V',
                     'grid_W', 'diaptr', 'trnd3d', 'scalar',
                     'UK_shelf_T', 'UK_shelf_U', 'UK_shelf_V'],
            'si3': ['icemod'],
            'medusa': ['ptrc_T', 'diad_T', 'ptrd_T']
            }

    @property
    def cfcompliant_output(self):
        '''
        Return "True" if the raw model output datestamp is CF-compliant.
        NEMO output data end-date is NOT CF-compliant.
        '''
        return False

    @property
    def rebuild_suffix(self):
        '''
        Returns dictionary with two keys, providing the suffix for components
        to rebuild:
            REGEX - REGular EXpression representing all PEs
            ZERO  - String representing PE0
        '''
        return {'REGEX': r'_\d{4}\.nc', 'ZERO': '_0000.nc'}

    @property
    def rebuild_iceberg_cmd(self):
        '''Returns the namelist value path for the icb_combrest.py script'''
        return self.naml.processing.exec_rebuild_icebergs

    @property
    def rebuild_iberg_traj_cmd(self):
        '''Returns the namelist value path for the icb_pp.py script'''
        return self.naml.processing.exec_rebuild_iceberg_trajectory

    @property
    def ncatted_cmd(self):
        '''Command: Exec + Args upto but not including filename(s)'''
        return self.naml.processing.ncatted_cmd

    @property
    def process_types(self):
        '''
        Return a list of tuples controlling the processing (creation/archive)
        of files other than restarts and means.
           (<type str> method_name, <type bool>)
        '''
        return [
            ('iceberg_trajectory',
             self.naml.archiving.archive_iceberg_trajectory),
            ('regional_extraction', self.naml.processing.extract_region),
            ]

    @property
    def iberg_trajectory_pattern(self):
        '''
        Return a regular expression matching iceberg trajecoty restart files
        '''
        return r'trajectory_icebergs_\d{6,8}(-\d{8})?'

    def model_realm(self, field):
        ''' Return the standard realm ID character for the model: o=ocean '''
        return 'i' if field in self.model_components['si3'] else 'o'

    def rst_set_stencil(self, rsttype):
        '''
        Return a regular expression to match means filenames output
        directly by the model.
        '''
        return r'^{P}o_{T1}_?\d{{8}}_restart{T2}(\.nc)?$'.format(P=self.prefix,
                                                                 T1=rsttype[0],
                                                                 T2=rsttype[1])

    def general_mean_stencil(self, field, base=None):
        '''
        Return a regular expression to match means filenames output
        directly by the model.
        '''
        return \
            r'^{P}o_{B}(_\d{{8,10}}){{2}}_{F}(([_\-]\d{{6,10}}){{2}})?' \
            r'(_\d{{4}})?(\.nc)?$'.format(P=self.prefix,
                                          B=base if base else r'\d+[hdmsy]',
                                          F=field)

    def buffer_rebuild(self, filetype):
        '''Returns the rebuild buffer for the given filetype'''
        if self.suite.finalcycle is True:
            buffer_rebuild = 0
        else:
            try:
                buffer_rebuild = int(
                    getattr(self.naml.processing,
                            'rebuild_{}_buffer'.format(filetype))
                    )
            except TypeError:
                # Buffer is None
                buffer_rebuild = 0
        return buffer_rebuild

    @timer.run_timer
    def move_to_share(self, pattern=None):
        '''
        Override move_to_share() to include modifying the means filename format
        '''
        super(NemoPostProc, self).move_to_share(pattern=pattern)
        # Modify region field names following filename convention re-naming
        self.region_fields = [f.replace('_', '-') for f in self.region_fields]

        if not pattern:
            # Standard pattern output - rebuild as required
            rebuildmeans = list(set(self.additional_means +
                                    [self.naml.processing.base_component]))
            self.rebuild_diagnostics(self.mean_fields, bases=rebuildmeans)
            self.rebuild_diagnostics(self.inst_fields)

    @timer.run_timer
    def rebuild_restarts(self):
        '''Rebuild partial restart files'''
        for rst in self.rsttypes:
            pattern = self.rst_set_stencil(rst).rstrip('$').lstrip('^')
            self.rebuild_fileset(self.share, pattern)

    @timer.run_timer
    def rebuild_diagnostics(self, fieldtypes, bases=r'\d+[hdmsyx]{1}'):
        '''Rebuild partial diagnostic fields files'''
        for field in fieldtypes:
            ncfname = netcdf_filenames.NCFilename('[a-z]*', self.suite.prefix,
                                                  self.model_realm(field),
                                                  custom='_' + field)
            for base in utils.ensure_list(bases):
                ncfname.base = base
                pattern = self.mean_stencil(ncfname).rstrip('.nc')
                self.rebuild_fileset(self.share, pattern)

    @timer.run_timer
    def rebuild_fileset(self, datadir, filetype):
        '''Rebuild partial files for given filetype'''
        # Recover any partial files which may have been left in temporary
        # directories due to failure (usually timeout) in a previous task.
        tmpdir_regex = 'rebuilding_' + filetype.upper().replace(r'\D', r'\d')
        tmp_dirs = utils.get_subset(datadir, tmpdir_regex)
        for tmp_dir in tmp_dirs:
            fullpath_tmp = os.path.join(datadir, tmp_dir)
            partial_files = utils.get_subset(
                fullpath_tmp,
                r'^.*{}$'.format(self.rebuild_suffix['REGEX'])
                )
            utils.move_files(partial_files, datadir, originpath=fullpath_tmp)
            shutil.rmtree(fullpath_tmp)

        bldfiles = utils.get_subset(
            datadir,
            r'^.*{}{}$'.format(filetype, self.rebuild_suffix['ZERO'])
            )
        if self.suite.finalcycle is not True:
            # Disregard any bldfiles produced during "future" cycles of
            # model-run task
            end_of_cycle = self.suite.cyclepoint.endcycle['strlist']
            for filename in reversed(bldfiles):
                date = self.get_date(filename, enddate=True)
                if ''.join([str(d).zfill(2) for d in date]) > \
                        ''.join(end_of_cycle):
                    bldfiles.remove(filename)
        bldfiles = sorted(bldfiles)

        buff = self.buffer_rebuild('restart') if \
            'restart' in filetype else self.buffer_rebuild('mean')
        while len(bldfiles) > buff:
            rebuild = True
            keep_components = False

            bldfile = bldfiles.pop(0)
            corename = bldfile.split(self.rebuild_suffix['ZERO'])[0]
            bldset = utils.get_subset(
                datadir,
                r'^{}{}$'.format(corename, self.rebuild_suffix['REGEX'])
                )

            if 'diaptr' in filetype:
                self.global_attr_to_zonal(datadir, bldset)

            elif 'restart' in filetype:
                if self.suite.finalcycle is True and len(bldfiles) == 0:
                    # Final restart file - Rebuild regardless of timestamp
                    #                    - Do not delete components
                    keep_components = True
                else:
                    # Rebuild requested timestamps
                    coredate = self.get_date(corename)
                    rebuild = self.timestamps(
                        coredate[1],
                        '01' if len(coredate) < 3 else coredate[2],
                        process='rebuild'
                        )

            if rebuild:
                utils.log_msg('Rebuilding: ' + corename, level='INFO')
                icode = self.rebuild_namelist(
                    datadir, corename, bldset,
                    omp=self.naml.processing.rebuild_omp_numthreads,
                    rebu_cache=self.naml.processing.rebu_cache,
                    deflate_lev=(self.naml.processing.compression_level if
                                 self.naml.processing.rebuild_compress else 0),
                    xchunk=self.naml.processing.xchunk,
                    ychunk=self.naml.processing.ychunk,
                    zchunk=self.naml.processing.zchunk,
                    tchunk=self.naml.processing.tchunk,
                    msk=self.naml.processing.msk_rebuild
                    )
            else:
                msg = 'Only rebuilding periodic files: ' + \
                    str(self.naml.processing.rebuild_restart_timestamps)
                utils.log_msg(msg, level='INFO')
                icode = 0

            if icode == 0:
                if not keep_components:
                    utils.log_msg('Deleting component files for: ' + corename,
                                  level='INFO')
                    utils.remove_files(bldset, path=datadir)

        if len(bldfiles) > 0:
            msg = 'Nothing to rebuild - {} {} files available ' \
                '({} retained).'.format(len(bldfiles), filetype, buff)
            utils.log_msg(msg, level='INFO')

    @timer.run_timer
    def global_attr_to_zonal(self, datadir, fileset):
        '''
        XIOS_v1.x has a bug which results in incorrect representation of
        mean data in some NEMO fields.
        Fix netcdf meta data in 2-dimensional given file[s] so that they
        represent zonal mean data and not global data.
        '''
        printtag = 'global_attr_to_zonal -'
        if not isinstance(fileset, list):
            fileset = [fileset]

        for filename in fileset:
            full_file = os.path.join(datadir, filename)

            # Run ncdump to interrogate the netcdf file
            output = self.suite.preprocess_file('ncdump', full_file, h='')
            global_ny = 'DOMAIN_size_globaly'
            global_nx = 'DOMAIN_size_globalx'
            pos_first_y = 'DOMAIN_position_first'
            pos_last_y = 'DOMAIN_position_last'

            for line in output.splitlines():
                # Split lines on '=', then ',' to get y dimension
                if ':DOMAIN_size_global' in line:
                    global_ny = re.split('=|,', line)[-1].strip(';').strip()
                    global_nx = re.split('=|,', line)[-2].strip()
                elif ':DOMAIN_position_first' in line:
                    pos_first_y = re.split('=|,', line)[-1].strip(';').strip()
                elif ':DOMAIN_position_last' in line:
                    pos_last_y = re.split('=|,', line)[-1].strip(';').strip()

            # Only process ncatted if there is an x dimension to the data
            # For GC2 this is false (the data does not need correcting)
            # For GC3 this is true and the data needs correcting using ncatted
            if global_nx.isdigit():
                notfound = [x for x in [global_ny, pos_first_y, pos_last_y] if
                            'DOMAIN' in x]
                if any(notfound):
                    msg = '{} attribute(s) {} not found in: '.\
                        format(printtag, ','.join(notfound))
                    utils.log_msg(msg + full_file, level='ERROR')

                cmd = ' '.join([
                    self.ncatted_cmd,
                    '-a DOMAIN_size_global,global,m,l,1,{}'.format(global_ny),
                    '-a DOMAIN_position_first,global,m,l,1,{}'.\
                        format(pos_first_y),
                    '-a DOMAIN_position_last,global,m,l,1,{}'.\
                        format(pos_last_y),
                    '-a ibegin,global,m,l,1',
                    full_file
                    ])

                # Use ncatted to change the attributes
                msg = '{} Changing nc file attributes using command: {}'.\
                    format(printtag, cmd)
                ret_code, output = utils.exec_subproc(cmd)
                if ret_code == 0:
                    msg = msg + '\nncatted - Successful for file {}'.\
                        format(full_file)
                    level = 'OK'
                else:
                    msg = msg + '\nncatted - Failed for file {}'.\
                        format(full_file)
                    level = 'ERROR'
                utils.log_msg(msg, level=level)
            else:
                utils.log_msg('{} 1D data, global attributes OK.'.\
                                  format(printtag),
                              level='OK')

    @timer.run_timer
    def rebuild_namelist(self, datadir, filebase, bldset,
                         omp=16, deflate_lev=0, rebu_cache=None,
                         xchunk=None, ychunk=None, zchunk=None, tchunk=None,
                         chunk=None, dims=None, msk=False):
        '''Create the namelist file required by the rebuild_nemo executable'''
        cmd = self.rebuild_cmd.replace('%F', 'rebuild_' + filebase.upper())
        try:
            namelist = cmd.split()[1]
            tempdir = False
        except IndexError:
            namelist = 'nam_rebuild'
            tempdir = True

        ndom = len(bldset)
        if tempdir:
            rebuild_dir = os.path.join(datadir,
                                       'rebuilding_' + filebase.upper())
            utils.create_dir(rebuild_dir)
        else:
            rebuild_dir = datadir

        namelistfile = os.path.join(rebuild_dir, namelist)
        txt = "&nam_rebuild\nfilebase='{}'\nndomain={}".format(filebase, ndom)
        if msk:
            txt += "\nl_maskout=.true."
        if dims:
            txt += "\ndims='{}','{}'".format(*dims)
        if chunk:
            txt += "\nnchunksize={}".format(chunk)
        if deflate_lev > 0:
            txt += "\ndeflate_level={}".format(deflate_lev)
            txt += "\nnc4_xchunk={}".format(xchunk)
            txt += "\nnc4_ychunk={}".format(ychunk)
            txt += "\nnc4_zchunk={}".format(zchunk)
            txt += "\nnc4_tchunk={}".format(tchunk)
            txt += "\nfchunksize={}".format(rebu_cache)
        txt += '\n/\n'
        open(namelistfile, 'w').write(txt)

        os.environ['OMP_NUM_THREADS'] = str(omp)
        if os.path.isfile(namelistfile):
            if tempdir:
                utils.move_files(bldset, rebuild_dir, originpath=datadir)
            icode, _ = utils.exec_subproc(cmd, cwd=rebuild_dir)

            rebuiltfile = os.path.join(rebuild_dir, filebase + '.nc')
            if icode != 0 or not os.path.isfile(rebuiltfile):
                icode = icode if icode != 0 else 900
            elif ('icebergs' in filebase) or ('icb' in filebase):
                # Additional processing required for iceberg restart files
                # pre NEMO 4.2: "icebergs" and post NEMO 4.2 "icb"
                icode = self.rebuild_icebergs(rebuild_dir, filebase, ndom)

            if tempdir:
                utils.move_files(bldset, datadir, originpath=rebuild_dir)

            if icode == 0:
                msg = 'Successfully rebuilt file: ' + rebuiltfile
                utils.log_msg(msg, level='INFO')
                if tempdir:
                    utils.move_files(rebuiltfile, datadir)
                utils.remove_files(namelistfile)
            else:
                msg = '{}: Error={}\n -> Failed to rebuild file: {}'.\
                    format(cmd, icode, rebuiltfile)
                if tempdir:
                    shutil.rmtree(rebuild_dir)
                utils.log_msg(msg, level='ERROR')
        else:
            utils.log_msg('Failed to create namelist file: ' + namelist,
                          level='WARN')
            icode = 910

        if tempdir:
            try:
                shutil.rmtree(rebuild_dir)
            except OSError:
                # Directory was previously removed following rebuild failure.
                # For debug_mode=False, the app exits following the failure.
                pass

        return icode

    @timer.run_timer
    def rebuild_icebergs(self, datadir, filebase, ndom):
        '''
        Additional post-processing is required to complete the rebuilding of
        iceberg restart files following use of the standard rebuild_nemo
        utility to rebuild the 2D fields.

        Iceberg data, stored as lists (data for each iceberg), is then
        collected is then added to the partially rebuilt file created by
        rebuild_nemo

        This routine is available on the NEMO repository, and is extracted
        from that source during the fcm_make_pp build app:

        fcm:NEMO/trunk/NEMOGCM/TOOLS/REBUILD_NEMO/icb_combrest.py
        '''
        cmd = 'python {} -f {} -n {} -o {}'.format(
            self.rebuild_iceberg_cmd, os.path.join(datadir, filebase + '_'),
            ndom, os.path.join(datadir, filebase + '.nc')
            )
        icode, output = utils.exec_subproc(cmd, cwd=datadir)
        # Currently the icb_combrest.py script always exits with icode=0
        # irrespective of success or failure.  Attempt to catch error message.
        if 'error' in output.lower() or icode != 0:
            msg = 'icb_combrest: Error={}\n\t{}'.format(icode, output)
            msg = msg + '\n -> Failed to rebuild file: ' + filebase
            utils.log_msg(msg, level='WARN')
            icode = icode if icode != 0 else -1
        else:
            msg = 'icb_combrest: Successfully rebuilt iceberg file ' + filebase
            utils.log_msg(msg, level='INFO')

        return icode

    @timer.run_timer
    def create_iceberg_trajectory(self):
        ''' Rebuild iceberg trajectory (diagnostic) files '''
        fn_stub = self.iberg_trajectory_pattern
        # Move to share if necessary
        if self.work != self.share:
            self.move_to_share(pattern=fn_stub + self.rebuild_suffix['REGEX'])

        # Rebuild each unique set of files we find in share
        for fname in utils.get_subset(self.share,
                                      fn_stub + self.rebuild_suffix['ZERO']):
            corename = fname.split(self.rebuild_suffix['ZERO'])[0]
            bldset = utils.get_subset(
                self.share,
                r'^{}{}$'.format(corename, self.rebuild_suffix['REGEX'])
                )
            outputfile = os.path.join(self.share,
                                      '{}o_{}.nc'.format(self.prefix,
                                                         corename))
            cmd = 'python {} -t {} -n {} -o {}'.format(
                self.rebuild_iberg_traj_cmd,
                os.path.join(self.share, corename + '_'),
                len(bldset),
                outputfile,
                )
            icode, output = utils.exec_subproc(cmd)
            if icode != 0:
                msg = 'icb_pp: Error={}\n\t{}'.format(icode, output)
                msg = msg + '\n -> Failed to rebuild file: ' + corename
                utils.log_msg(msg, level='ERROR')
            else:
                msg = 'icb_pp: Successfully rebuilt iceberg trajectory file: '
                utils.log_msg(msg + corename, level='INFO')
                utils.remove_files(bldset, path=self.share)

    @timer.run_timer
    def archive_iceberg_trajectory(self):
        ''' Archive iceberg trajectory (diagnostic) files '''
        arch_rtn = self.archive_files(utils.get_subset(
            self.share,
            r'^{}o_{}\.nc$'.format(self.prefix,
                                   self.iberg_trajectory_pattern)
            ))

        self.clean_archived_files(arch_rtn, 'iceberg_trajectory')

    @timer.run_timer
    def create_regional_extraction(self):
        ''' Extract a region from global netCDF files '''
        utils.create_dir(self.diagsdir)

        for field in self.region_fields:
            ncfname = netcdf_filenames.NCFilename('[a-z]*', self.suite.prefix,
                                                  self.model_realm(field),
                                                  custom='_' + field)
            pattern = self.mean_stencil(ncfname)
            for filename in utils.get_subset(self.share, pattern):
                try:
                    xdim, xmin, xmax, ydim, ymin, ymax = \
                        self.naml.processing.region_dimensions
                    xdim = xdim.replace('%G', field[-1])
                    ydim = ydim.replace('%G', field[-1])
                except ValueError:
                    msg = 'Unable to determine x-y dimensions from &nemo' + \
                        'postproc/regional_dimensions: '
                    utils.log_msg(
                        msg + str(self.naml.processing.region_dimensions),
                        level='ERROR'
                        )
                    continue

                rcode = 0
                # Check whether this is already an extracted region
                full_fn = os.path.join(self.share, filename)
                output = self.suite.preprocess_file('ncdump', full_fn, h='')
                output = [l.strip(';').strip() for l in output.split('\n')]
                if '{} = {}'.format(xdim, (xmax - xmin + 1)) in output:
                    msg = 'This is a regional file. No extraction necessary'
                    utils.log_msg(msg, level='INFO')
                else:
                    # Use ncks to extract the required region
                    utils.log_msg('Extracting region from netCDF file...',
                                  level='INFO')
                    rcode, output = self.suite.preprocess_file(
                        'ncks', full_fn, O='', a='',
                        d_1=','.join([xdim, str(xmin), str(xmax)]),
                        d_2=','.join([ydim, str(ymin), str(ymax)])
                        )

                # Compress file if necessary
                if rcode == 0 and (self.naml.processing.compression_level > 0):
                    rcode = self.compress_file(
                        full_fn, self.naml.processing.compress_netcdf,
                        compression=self.naml.processing.compression_level,
                        chunking=self.naml.processing.region_chunking_args
                        )

                # Move file to archive directory
                if rcode == 0 and field not in self.mean_fields:
                    utils.move_files(full_fn, self.diagsdir)

    @timer.run_timer
    def archive_regional_extraction(self):
        ''' Archive a regional extraction from global netCDF files '''
        for field in self.region_fields:
            ncfname = netcdf_filenames.NCFilename('[a-z]*', self.suite.prefix,
                                                  self.model_realm(field),
                                                  custom='_' + field)
            pattern = '^{}$'.format(self.mean_stencil(ncfname))
            a_files = utils.get_subset(self.diagsdir, pattern)
            a_files = utils.add_path(a_files, self.diagsdir)
            arch_rtn = self.archive_files(a_files)

            self.clean_archived_files(arch_rtn, 'UK Shelf region')

    @timer.run_timer
    def preprocess_meanset(self, meanset):
        ''' Pre-process component files prior to creating a mean '''
        filenames = utils.add_path(meanset, self.share)
        changes = fix_nemo_cell_methods(filenames)
        if changes:
            utils.log_msg('Corrected cell_methods on NEMO means files:',
                          level='INFO')
            utils.log_msg('\n'.join(changes), level='INFO')


def fix_nemo_cell_methods(filenames):
    '''
    Overwrite the cell_methods of certain variables to allow mean_nemo
    processes to correctly apply volume and thickness weights when
    averaging over time. Returns a list of messages describing the
    changes made.
    Variables: filenames = iterable of file names to be operated on.
    '''
    msgs = []
    # Set file extension for temporary files to ".tmp"
    tmpext = '.tmp'
    tmp_files = utils.copy_files(filenames, tmp_ext=tmpext)
    for filename in tmp_files:
        ncid = netcdf_utils.get_dataset(filename, action='r+')
        for var in ncid.variables:
            msg = None
            if var in THICKNESS_WEIGHTED_VARIABLES:
                ncid.variables[var].cell_methods = THICK_WEIGHT_CELL_METHODS
                msg = ('Overwriting cell_methods for variable {} in file '
                       '{} with "time: mean (thickness weighted)"'
                       '').format(var, filename)
            elif var in VOLUME_WEIGHTED_VARIABLES:
                ncid.variables[var].cell_methods = VOL_WEIGHT_CELL_METHODS
                msg = ('Overwriting cell_methods for variable {} in file '
                       '{} with "time: mean (volume weighted)"'
                       '').format(var, filename)
            if msg is not None:
                msgs.append(msg)
        ncid.close()
        try:
            os.rename(filename, os.path.splitext(filename)[0])
        except OSError:
            err = 'fix_nemo_cell_methods: Failed to rename modifed mean file'
            utils.log_msg(err, level='ERROR')

    return msgs


INSTANCE = ('nemocicepp.nl', NemoPostProc)


if __name__ == '__main__':
    pass
