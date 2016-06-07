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
    nemo.py

DESCRIPTION
    Class definition for NemoPostProc - holds NEMO model properties
    and methods
'''
import os
import re

import utils
import modeltemplate as mt


class NemoPostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the NEMO post processing application.
    '''
    @property
    def fields(self):
        return ('grid_T', 'grid_U', 'grid_V', 'grid_W', 'diaptr', 'trnd3d',)

    @property
    def rsttypes(self):
        return ('', 'icebergs')

    @property
    def set_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) set

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        return {
            mt.RR: lambda y, m, s, f:
                   r'^{P}o_{F}_?\d{{8}}_restart(\.nc)?$'.
                   format(P=self.prefix, F=f),
            mt.MM: lambda y, m, s, f:
                   r'^{P}o_{B}_\d{{8}}_{Y}{M}\d{{2}}_{F}\.nc$'.
                   format(P=self.prefix, B=self.month_base, Y=y, M=m, F=f),
            mt.SS: lambda y, m, s, f:
                   r'^{P}o_1m_({Y1}{M1}|{Y2}{M2}|{Y2}{M3})01_\d{{8}}_{F}\.nc$'.
                   format(P=self.prefix,
                          Y1=str(int(y) - s[3]) if isinstance(s[3], int) else y,
                          Y2=y,
                          M1=s[0],
                          M2=s[1],
                          M3=s[2],
                          F=f),
            mt.AA: lambda y, m, s, f:
                   r'^{P}o_1s_\d{{8}}_{Y}\d{{2}}(28|29|30|31)_{F}\.nc$'.
                   format(P=self.prefix, Y=y, F=f),
        }

    @property
    def end_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) end

        The same 2 arguments (season and field) are required to access any
        indivdual regular expression regardless of the need to use them.
        This is a consequence of the @property nature of the method
        '''
        return {
            mt.RR: None,
            mt.MM: lambda s, f:
                   r'^{P}o_{B}_\d{{8}}_\d{{6}}(28|29|30|31)_{F}\.nc$'.
                   format(P=self.prefix, B=self.month_base, F=f),
            mt.SS: lambda s, f: r'^{P}o_1m_\d{{4}}{M1}01_\d{{8}}_{F}\.nc$'.
                   format(P=self.prefix, M1=s[2], F=f),
            mt.AA: lambda s, f: r'^{P}o_1s_\d{{4}}0901_\d{{8}}_{F}\.nc$'.
                   format(P=self.prefix, F=f),
        }

    @property
    def mean_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) mean

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        return {
            mt.XX: lambda y, m, s, f:
                   r'^{P}o_{B}_\d{{8,10}}_\d{{8,10}}_{F}(\.nc)?$'.
                   format(P=self.prefix, B=y if y else r'\d+[hdmsy]', F=f),
            mt.MM: lambda y, m, s, f: r'{P}o_1m_{Y}{M}01_{Y}{M}{L}_{F}.nc'.
                   format(P=self.prefix, Y=y, M=m,
                          L=self.suite.monthlength(m), F=f),
            mt.SS: lambda y, m, s, f: r'{P}o_1s_{Y1}{M1}01_{Y2}{M2}{L}_{F}.nc'.
                   format(P=self.prefix,
                          Y1=str(int(y) - s[3]) if isinstance(s[3], int) \
                              else y,
                          Y2=y,
                          M1=s[0],
                          M2=s[2],
                          L=self.suite.monthlength(s[2]),
                          F=f),
            mt.AA: lambda y, m, s, f: r'{P}o_1y_{Y1}1201_{Y2}1130_{F}.nc'.
                   format(P=self.prefix,
                          Y1=y if '*' in y else (int(y)-1),
                          Y2=y,
                          F=f),
        }

    @property
    def rebuild_iceberg_cmd(self):
        '''Returns the namelist value path for the icb_combrest.py script'''
        return self.nl.exec_rebuild_icebergs

    @property
    def rebuild_iberg_traj_cmd(self):
        '''Returns the namelist value path for the icb_pp.py script'''
        return self.nl.exec_rebuild_iceberg_trajectory

    @property
    def ncatted_cmd(self):
        '''Command: Exec + Args upto but not including filename(s)'''
        return self.nl.ncatted_cmd

    @property
    def archive_types(self):
        '''
        Additional archiving methods to call for files
        other than restarts and means.
        Returns a list of tuples: (method_name, bool)
        '''
        return [('iceberg_trajectory', self.nl.archive_iceberg_trajectory),]

    def buffer_rebuild(self, filetype):
        '''Returns the rebuild buffer for the given filetype'''
        buffer_rebuild = getattr(self.nl, 'buffer_rebuild_' + filetype)
        return buffer_rebuild if buffer_rebuild else 0

    @staticmethod
    def get_date(fname):
        for string in fname.split('_'):
            if string.isdigit():
                return string[:4], string[4:6], string[6:8]
        utils.log_msg('Unable to get date for file:\n\t' + fname, level=3)

    def rebuild_restarts(self):
        '''Rebuild partial restart files'''
        for rst in self.rsttypes:
            pattern = self.set_stencil[mt.RR](None, None, None, rst).\
                rstrip('$').lstrip('^')
            self.rebuild_fileset(self.share, pattern)

    def rebuild_means(self):
        '''Rebuild partial means files'''
        rebuildmeans = self.additional_means + ['10d']
        for field in self.fields:
            for mean in set(rebuildmeans):
                pattern = self.mean_stencil[mt.XX](mean, None, None, field).\
                    rstrip('$').lstrip('^')
                self.rebuild_fileset(self.share, pattern, rebuildall=True)

    def rebuild_fileset(self, datadir, filetype, suffix='_0000.nc',
                        rebuildall=False):
        '''Rebuild partial files for given filetype'''
        bldfiles = utils.get_subset(datadir,
                                    r'^.*{}.*{}$'.format(filetype, suffix))
        buff = self.buffer_rebuild('rst') if \
            'restart' in filetype else self.buffer_rebuild('mean')
        rebuild_required = len(bldfiles) > buff
        while len(bldfiles) > buff:
            bldfile = bldfiles.pop(0)
            corename = bldfile.split(suffix)[0]
            bldset = utils.get_subset(datadir,
                                      r'^{}_\d{{4}}\.nc$'.format(corename))

            year = month = day = None
            for part in corename.split('_'):
                # Retrieve the data start-date from the filename
                if re.search('^\d{8}$', part):
                    year, month, day = self.get_date(part)
                    break

            if filetype == 'diaptr':
                self.global_attr_to_zonal(datadir, bldset)

            if rebuildall or self.timestamps(month, day, process='rebuild'):
                utils.log_msg('Rebuilding: ' + corename, level=1)
                icode = self.rebuild_namelist(datadir, corename,
                                              len(bldset), omp=1)
            else:
                msg = 'Only rebuilding periodic files: ' + \
                    str(self.nl.rebuild_timestamps)
                utils.log_msg(msg, level=1)
                icode = 0

            if icode == 0:
                filename = os.path.join(datadir, corename + '.nc')
                if os.path.isfile(filename):
                    self.check_fileformat(filename, (year, month, day),
                                          filetype)

                if not self.suite.finalcycle or 'restart' not in corename:
                    utils.log_msg('Deleting component files for: ' + corename,
                                  level=1)
                    utils.remove_files(bldset, self.share)

        if bldfiles and not rebuild_required:
            msg = 'Nothing to rebuild - {} {} files available ' \
                '({} retained).'.format(len(bldfiles), filetype, buff)
            utils.log_msg(msg, level=1)

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
                if 'DOMAIN_size_global' in line:
                    global_ny = re.split('=|,', line)[-1].strip(';').strip()
                elif 'DOMAIN_position_first' in line:
                    pos_first_y = re.split('=|,', line)[-1].strip(';').strip()
                elif 'DOMAIN_position_last' in line:
                    pos_last_y = re.split('=|,', line)[-1].strip(';').strip()

            notfound = [x for x in [global_ny, pos_first_y, pos_last_y] if
                        'DOMAIN' in x]
            if any(notfound):
                msg = 'global_attr_to_zonal - attribute(s) {} not found in: '.\
                    format(','.join(notfound))
                utils.log_msg(msg + full_file, level=5)

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
                level = 2
            else:
                msg = msg + '\nncatted - Failed for file {}'.format(full_file)
                level = 5
            utils.log_msg(msg, level=level)

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
        txt += '\n/'
        open(namelistfile, 'w').write(txt)

        os.environ['OMP_NUM_THREADS'] = str(omp)
        if os.path.isfile(namelistfile):
            icode, _ = utils.exec_subproc(self.rebuild_cmd, cwd=datadir)
            rebuiltfile = os.path.join(datadir, filebase + '.nc')
            if not os.path.isfile(rebuiltfile):
                msg = 'Rebuilt file does not exist: ' + rebuiltfile
                utils.log_msg(msg, level=3)
                icode = 900
            else:
                if icode == 0 and 'icebergs' in filebase:
                    # Additional processing required for iceberg restart files
                    icode = self.rebuild_icebergs(datadir, filebase, ndom)
                if icode == 0:
                    msg = 'Successfully rebuilt file: ' + rebuiltfile
                    utils.log_msg(msg, level=2)
                    utils.remove_files(namelistfile)
                else:
                    msg = '{}: Error={}\n -> Failed to rebuild file: {}'.\
                        format(self.rebuild_cmd, icode, rebuiltfile)
                    utils.log_msg(msg, level=4)
                    utils.catch_failure(self.nl.debug)
        else:
            utils.log_msg('Failed to create namelist file: ' + namelist,
                          level=3)
            icode = 910
        return icode

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
            utils.log_msg(msg, level=4)
            utils.catch_failure(self.nl.debug)
            icode = -1
        else:
            msg = 'icb_combrest: Successfully rebuilt iceberg file ' + filebase
            utils.log_msg(msg, level=1)

        return icode

    def check_fileformat(self, inputfile, date, filetype):
        '''
        Output file format for means files changed at vn3.5.
        This function renames rebuilt means files with the original format
        prior to their use in creating other means.
        '''
        mean_period = None
        for base in mt.MONTH_BASE:
            if '_{}_'.format(base) in inputfile:
                mean_period = base
                period = re.match(r'^(?P<num>\d+)(?P<per>[a-zA-Z]+)$',
                                  mean_period)
                if period.group('per').lower() == 'h':
                    msg = 'NEMO check_fileformat: hourly means not implemented'
                    utils.log_msg(msg, level=3)
                    return
                try:
                    mean_day2 = int(date[2]) + int(period.group('num')) - 1
                except ValueError:
                    msg = 'NEMO check_fileformat: Date format is incorrect:'
                    utils.log_msg(msg + filetype, level=5)
                break

        if not mean_period:
            return

        try:
            field = [f for f in self.fields if re.search(f, filetype)][0]
        except IndexError:
            msg = 'NEMO check_fileformat: Cannot obtain field from filename:'
            utils.log_msg(msg + filetype, level=5)

        args = (r'\d{4}', r'\d{2}', None, field)
        if not re.match(self.set_stencil[mt.MM](*args),
                        os.path.basename(inputfile)):
            template = r'{0}o_{1}_{2}{3}{4}_{2}{3}{5:0>2d}_{6}.nc'.\
                format(self.prefix, mean_period, date[0], date[1], date[2],
                       mean_day2, field)
            os.rename(inputfile, os.path.join(self.share, template))

    def archive_iceberg_trajectory(self):
        '''Rebuild and archive iceberg trajectory (diagnostic) files'''
        fn_stub = r'trajectory_icebergs_\d{6}'
	# Move to share if necessary
        if self.work != self.share:
            pattern = fn_stub + r'_\d{4}.nc'
            self.move_to_share(pattern)

        # Rebuild each unique set of files we find in share
        suffix = '_0000.nc'
        for fname in utils.get_subset(self.share, fn_stub + suffix):
            corename = fname.split(suffix)[0]
            bldset = utils.get_subset(self.share,
                                      r'^{}_\d{{4}}.nc$'.format(corename))
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
                utils.log_msg(msg, level=4)
                utils.catch_failure(self.nl.debug)
            else:
                msg = 'icb_pp: Successfully rebuilt iceberg trajectory file: '
                utils.log_msg(msg + corename, level=1)
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
                utils.remove_files(del_files, self.share)


INSTANCE = ('nemocicepp.nl', NemoPostProc)


if __name__ == '__main__':
    pass
