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
    nemo.py

DESCRIPTION
    Class definition for NemoPostProc - holds NEMO model properties
    and methods
'''
import os
import re

import timer
import utils
import modeltemplate as mt
import netcdf_filenames

class NemoPostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the NEMO post processing application.
    '''
    @property
    def _fields(self):
        'Returns the fieldsfile types to be processed'
        if self.naml.means_fieldsfiles:
            fields = self.naml.means_fieldsfiles
            if not isinstance(fields, list):
                fields = [fields]
        else:
            fields = []
            for val in self.model_components.values():
                fields += val
        return tuple(sorted(fields))

    @property
    def rsttypes(self):
        '''
        Restart file types.
        Tuple( Filetype tag immediately following "RUNIDo_" in filename,
               Filetype tag immediately following "restart" in filename )
        '''
        return (('', ''), ('icebergs', ''), ('', '_trc'))

    @property
    def model_components(self):
        '''Name of model component, to be used as a prefix to archived files '''
        return {
            'nemo': ['grid_T', 'grid_U', 'grid_V',
                     'grid_W', 'diaptr', 'trnd3d'],
            'medusa': ['ptrc_T', 'diad_T']
            }

    @property
    def model_realm(self):
        ''' Return the standard realm ID character for the model: o=ocean '''
        return 'o'

    @property
    def set_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) set

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        set_stencil = super(NemoPostProc, self).set_stencil
        set_stencil[mt.RR] = lambda rsttype: \
            r'^{P}o_{T1}_?\d{{8}}_restart{T2}(\.nc)?$'.\
            format(P=self.prefix, T1=rsttype[0], T2=rsttype[1])
        return set_stencil

    @property
    def mean_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) mean
        '''
        mean_stencil = super(NemoPostProc, self).mean_stencil
        mean_stencil[mt.XX] = lambda field, base=None: \
            r'^{P}o_{B}(_\d{{8,10}}){{2}}_{F}(([_\-]\d{{6,10}}){{2}})?' \
            r'(_\d{{4}})?(\.nc)?$'.format(P=self.prefix,
                                          B=base if base else r'\d+[hdmsy]',
                                          F=field)
        return mean_stencil

    @property
    def rebuild_suffix(self):
        '''
        Returns dictionary with two keys, profiding the suffix for components
        to rebuild:
            REGEX - REGular EXpression representing all PEs
            ZERO  - String representing PE0
        '''
        return {'REGEX': r'_\d{4}\.nc', 'ZERO': '_0000.nc'}

    @property
    def rebuild_iceberg_cmd(self):
        '''Returns the namelist value path for the icb_combrest.py script'''
        return self.naml.exec_rebuild_icebergs

    @property
    def rebuild_iberg_traj_cmd(self):
        '''Returns the namelist value path for the icb_pp.py script'''
        return self.naml.exec_rebuild_iceberg_trajectory

    @property
    def ncatted_cmd(self):
        '''Command: Exec + Args upto but not including filename(s)'''
        return self.naml.ncatted_cmd

    @property
    def archive_types(self):
        '''
        Additional archiving methods to call for files
        other than restarts and means.
        Returns a list of tuples: (method_name, bool)
        '''
        return [('iceberg_trajectory', self.naml.archive_iceberg_trajectory)]

    def buffer_rebuild(self, filetype):
        '''Returns the rebuild buffer for the given filetype'''
        buffer_rebuild = getattr(self.naml, 'buffer_rebuild_' + filetype)
        return buffer_rebuild if buffer_rebuild else 0

    @timer.run_timer
    def move_to_share(self, pattern=None):
        '''
        Override move_to_share() to include modifying the means filename format
        '''
        super(NemoPostProc, self).move_to_share(pattern=pattern)
        if not pattern:
            # Standard means - rebuild as required
            self.rebuild_means()

    @timer.run_timer
    def rebuild_restarts(self):
        '''Rebuild partial restart files'''
        for rst in self.rsttypes:
            pattern = self.set_stencil[mt.RR](rst).rstrip('$').lstrip('^')
            self.rebuild_fileset(self.share, pattern)

    @timer.run_timer
    def rebuild_means(self):
        '''Rebuild partial means files'''
        rebuildmeans = self.additional_means + [self.month_base]
        ncfname = netcdf_filenames.NCFilename('[a-z]*', self.suite.prefix,
                                              self.model_realm)
        for field in self.fields:
            ncfname.custom = '_' + field
            for mean in set(rebuildmeans):
                ncfname.base = mean
                pattern = self.mean_stencil['All'](ncfname).rstrip('.nc')
                self.rebuild_fileset(self.share, pattern, rebuildall=True)

    @timer.run_timer
    def rebuild_fileset(self, datadir, filetype, rebuildall=False):
        '''Rebuild partial files for given filetype'''
        bldfiles = utils.get_subset(
            datadir,
            r'^.*{}{}$'.format(filetype, self.rebuild_suffix['ZERO'])
            )
        buff = self.buffer_rebuild('rst') if \
            'restart' in filetype else self.buffer_rebuild('mean')
        rebuild_required = len(bldfiles) > buff
        while len(bldfiles) > buff:
            bldfile = bldfiles.pop(0)
            corename = bldfile.split(self.rebuild_suffix['ZERO'])[0]
            bldset = utils.get_subset(
                datadir,
                r'^{}{}$'.format(corename, self.rebuild_suffix['REGEX'])
                )

            if 'diaptr' in filetype:
                self.global_attr_to_zonal(datadir, bldset)

            coredate = self.get_date(corename)
            if self.timestamps(coredate[1],
                               '01' if len(coredate) < 3 else coredate[2],
                               process='rebuild') or rebuildall:
                utils.log_msg('Rebuilding: ' + corename, level='INFO')
                icode = self.rebuild_namelist(datadir, corename,
                                              len(bldset), omp=1)
            else:
                msg = 'Only rebuilding periodic files: ' + \
                    str(self.naml.rebuild_timestamps)
                utils.log_msg(msg, level='INFO')
                icode = 0

            if icode == 0:
                if not self.suite.finalcycle or 'restart' not in corename:
                    utils.log_msg('Deleting component files for: ' + corename,
                                  level='INFO')
                    utils.remove_files(bldset, datadir)

        if bldfiles and not rebuild_required:
            msg = 'Nothing to rebuild - {} {} files available ' \
                '({} retained).'.format(len(bldfiles), filetype, buff)
            utils.log_msg(msg, level='INFO')

    @timer.run_timer
    def global_attr_to_zonal(self, datadir, fileset):
        '''
        XIOS_v1.x has a bug which results in incorrect representation of
        mean data in some NEMO fields.
        Fix netcdf meta data in given file[s] so that they represent
        zonal mean data and not global data.
        '''
        if not isinstance(fileset, list):
            fileset = [fileset]

        for filename in fileset:
            full_file = os.path.join(datadir, filename)

            # Run ncdump to interrogate the netcdf file
            output = self.suite.preprocess_file('ncdump', full_file, h='')
            global_ny = 'DOMAIN_size_global'
            pos_first_y = 'DOMAIN_position_first'
            pos_last_y = 'DOMAIN_position_last'

            for line in output.splitlines():
                # Split lines on '=', then ',' to get y dimension
                if ':DOMAIN_size_global' in line:
                    global_ny = re.split('=|,', line)[-1].strip(';').strip()
                elif ':DOMAIN_position_first' in line:
                    pos_first_y = re.split('=|,', line)[-1].strip(';').strip()
                elif ':DOMAIN_position_last' in line:
                    pos_last_y = re.split('=|,', line)[-1].strip(';').strip()

            notfound = [x for x in [global_ny, pos_first_y, pos_last_y] if
                        'DOMAIN' in x]
            if any(notfound):
                msg = 'global_attr_to_zonal - attribute(s) {} not found in: '.\
                    format(','.join(notfound))
                utils.log_msg(msg + full_file, level='ERROR')

            cmd = ' '.join([
                self.ncatted_cmd,
                '-a DOMAIN_size_global,global,m,l,1,{}'.format(global_ny),
                '-a DOMAIN_position_first,global,m,l,1,{}'.format(pos_first_y),
                '-a DOMAIN_position_last,global,m,l,1,{}'.format(pos_last_y),
                '-a ibegin,global,m,l,1',
                full_file
                ])

            # Use ncatted to change the attributes
            msg = 'global_attr_to_zonal - Changing nc file attributes ' \
                'using command: ' + cmd
            ret_code, output = utils.exec_subproc(cmd)
            if ret_code == 0:
                msg = msg + '\nncatted - Successful for file {}'.\
                    format(full_file)
                level = 'OK'
            else:
                msg = msg + '\nncatted - Failed for file {}'.format(full_file)
                level = 'ERROR'
            utils.log_msg(msg, level=level)

    @timer.run_timer
    def rebuild_namelist(self, datadir, filebase, ndom,
                         omp=16, chunk=None, dims=None):
        '''Create the namelist file required by the rebuild_nemo executable'''
        namelist = 'nam_rebuild'
        namelistfile = os.path.join(datadir, namelist)
        txt = "&{}\nfilebase='{}'\nndomain={}".format(namelist, filebase, ndom)
        if dims:
            txt += "\ndims='{}','{}'".format(*dims)
        if chunk:
            txt += "\nnchunksize={}".format(chunk)
        txt += '\n/\n'
        open(namelistfile, 'w').write(txt)

        os.environ['OMP_NUM_THREADS'] = str(omp)
        if os.path.isfile(namelistfile):
            icode, _ = utils.exec_subproc(self.rebuild_cmd, cwd=datadir)
            rebuiltfile = os.path.join(datadir, filebase + '.nc')
            if icode != 0 or not os.path.isfile(rebuiltfile):
                icode = icode if icode != 0 else 900
            elif 'icebergs' in filebase:
                # Additional processing required for iceberg restart files
                icode = self.rebuild_icebergs(datadir, filebase, ndom)

            if icode == 0:
                msg = 'Successfully rebuilt file: ' + rebuiltfile
                utils.log_msg(msg, level='INFO')
                utils.remove_files(namelistfile)
            else:
                msg = '{}: Error={}\n -> Failed to rebuild file: {}'.\
                    format(self.rebuild_cmd, icode, rebuiltfile)
                utils.log_msg(msg, level='ERROR')
        else:
            utils.log_msg('Failed to create namelist file: ' + namelist,
                          level='WARN')
            icode = 910
        return icode

    @timer.run_timer
    def rebuild_icebergs(self, datadir, filebase, ndom):
        '''
        Additional postp-processing is required to complete the rebuilding of
        iceberg restart files following use of the standard rebuild_nemo
        utility to rebuild the 2D fields.

        Iceberg data, stored as lists (data for each iceberg), is then
        collected is then added to the partially rebuilt file created by
        rebuild_nemo

        This routine is available on the NEMO repository, and is extracted
        from that source during the fcm_make_pp build app:

        fcm:NEMO/trunk/NEMOGCM/TOOLS/REBUILD_NEMO/icb_combrest.py
        '''
        cmd = 'python2.7 {} -f {} -n {} -o {}'.format(
            self.rebuild_iceberg_cmd, os.path.join(datadir, filebase + '_'),
            ndom, os.path.join(datadir, filebase + '.nc')
            )
        icode, output = utils.exec_subproc(cmd, cwd=datadir)
        # Currently the icb_combrest.py script always exits with icode=0
        # irrespective of success or failure.  Attempt to catch error message.
        if 'error' in output.lower() or icode != 0:
            msg = 'icb_combrest: Error={}\n\t{}'.format(icode, output)
            msg = msg + '\n -> Failed to rebuild file: ' + filebase
            utils.log_msg(msg, level='ERROR')
            icode = -1
        else:
            msg = 'icb_combrest: Successfully rebuilt iceberg file ' + filebase
            utils.log_msg(msg, level='INFO')

        return icode

    @timer.run_timer
    def archive_iceberg_trajectory(self):
        '''Rebuild and archive iceberg trajectory (diagnostic) files'''
        fn_stub = r'trajectory_icebergs_\d{6}'
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
            cmd = 'python2.7 {} -t {} -n {} -o {}'.format(
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

        # Archive and delete from local disk
        arch_files = self.archive_files(
            utils.get_subset(self.share,
                             r'^{}o_{}.nc$'.format(self.prefix, fn_stub))
            )
        if arch_files:
            del_files = [fn for fn in arch_files if arch_files[fn] != 'FAILED']
            if del_files:
                msg = 'iceberg_trajectory: Deleting archived files: \n\t'
                utils.log_msg(msg + '\n\t'.join(del_files))
                if utils.get_debugmode():
                    # Append "ARCHIVED" suffix to files, rather than deleting
                    for fname in del_files:
                        fname = os.path.join(self.share, fname)
                        os.rename(fname, fname + '_ARCHIVED')
                else:
                    utils.remove_files(del_files, path=self.share)


INSTANCE = ('nemocicepp.nl', NemoPostProc)


if __name__ == '__main__':
    pass
