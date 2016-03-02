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
            mt.RR: lambda y, m, s, f: '^{}o_{}_?\d{{8}}_restart(\.nc)?$'.
            format(self.prefix, f),
            mt.MM: lambda y, m, s, f: '^{}o_10d_\d{{8}}_{}{}\d{{2}}_{}\.nc$'.
            format(self.prefix, y, m, f),
            mt.SS: lambda y, m, s, f:
                '^{}o_1m_({}{}|{}{}|{}{})01_\d{{8}}_{}\.nc$'.format(
                self.prefix,
                y if not isinstance(s[3], int) else str(int(y) - s[3]),
                s[0], y, s[1], y, s[2], f
                ),
            mt.AA: lambda y, m, s, f: '^{}o_1s_\d{{8}}_{}\d{{2}}30_{}\.nc$'.
            format(self.prefix, y, f),
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
            mt.MM: lambda s, f: '^{}o_10d_\d{{6}}21_\d{{6}}30_{}\.nc$'.format(
                self.prefix, f
                ),
            mt.SS: lambda s, f: '^{}o_1m_\d{{4}}{}01_\d{{8}}_{}\.nc$'.format(
                self.prefix, s[2], f
                ),
            mt.AA: lambda s, f: '^{}o_1s_\d{{4}}0901_\d{{8}}_{}\.nc$'.format(
                self.prefix, f
                ),
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
            mt.MM: lambda y, m, s, f: '{}o_1m_{}{}01_{}{}30_{}.nc'.format(
                self.prefix, y, m, y, m, f
                ),
            mt.SS: lambda y, m, s, f: '{}o_1s_{}{}01_{}{}30_{}.nc'.format(
                self.prefix,
                y if not isinstance(s[3], int) else str(int(y) - s[3]),
                s[0], y, s[2], f
                ),
            mt.AA: lambda y, m, s, f: '{}o_1y_{}1201_{}1130_{}.nc'.format(
                self.prefix, y if '*' in y else (int(y)-1), y, f
                ),
        }

    @property
    def rebuild_cmd(self):
        return self.nl.exec_rebuild

    @property
    def rebuild_iceberg_cmd(self):
        '''Returns the namelist value path for the icb_combrest.py script'''
        return self.nl.exec_rebuild_icebergs

    def buffer_rebuild(self, filetype):
        '''Returns the rebuild buffer for the given filetype'''
        buffer_rebuild = getattr(self.nl, 'buffer_rebuild_' + filetype)
        return buffer_rebuild if buffer_rebuild else 0

    @property
    def means_cmd(self):
        return self.nl.means_cmd

    @staticmethod
    def get_date(fname):
        for string in fname.split('_'):
            if string.isdigit():
                return string[:4], string[4:6], string[6:8]
        utils.log_msg('Unable to get date for file:\n\t' + fname, level=3)

    def rebuild_restarts(self):
        '''Rebuild partial restart files'''
        for rst in self.rsttypes:
            # Strip '$' from end of pattern
            pattern = self.set_stencil[mt.RR](None, None, None, rst)[:-1]
            self.rebuild_fileset(self.share, pattern)

    def rebuild_means(self):
        '''Rebuild partial means files'''
        for field in self.fields:
            self.rebuild_fileset(self.share, field, rebuildall=True)

    def rebuild_fileset(self, datadir, filetype, suffix='_0000.nc',
                        rebuildall=False):
        '''Rebuild partial files for given filetype'''
        bldfiles = utils.get_subset(datadir,
                                    '^.*{}{}$'.format(filetype, suffix))
        buff = self.buffer_rebuild('rst') if \
            'restart' in filetype else self.buffer_rebuild('mean')
        rebuild_required = len(bldfiles) > buff
        while len(bldfiles) > buff:
            bldfile = bldfiles.pop(0)
            corename = bldfile.split(suffix)[0]
            bldset = utils.get_subset(datadir,
                                      '^{}_\d{{4}}\.nc$'.format(corename))

            year = month = day = None
            for part in reversed(corename.split('_')):
                if re.search('\d{8}', part):
                    year, month, day = self.get_date(part)
                    break

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

                if not self.suite.finalcycle:
                    utils.log_msg('Deleting component files for: ' + corename,
                                  level=1)
                    utils.remove_files(bldset, self.share)

        if bldfiles and not rebuild_required:
            msg = 'Nothing to rebuild - {} {} files available ' \
                '({} retained).'.format(len(bldfiles), filetype, buff)
            utils.log_msg(msg, level=1)

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
        Output file format changed at vn3.5.
        This function renames rebuilt files with the original format
        '''
        if 'restart' in filetype:
            field = ''
            period = mt.RR
            template = '{}o_{}{}{}_restart.nc'.format(self.prefix, date[0],
                                                      date[1], date[2])
        else:
            field = filetype
            period = mt.MM
            template = '{0}o_10d_{1}{2}{3}_{1}{2}{4:0>2d}_{5}.nc'.\
                format(self.prefix, date[0], date[1], date[2],
                       int(date[2])+9, field)

            args = ('\d{4}', '\d{2}', None, field)
            if not re.match(self.set_stencil[period](*args),
                            os.path.basename(inputfile)):
                os.rename(inputfile, os.path.join(self.share, template))


INSTANCE = ('nemocicepp.nl', NemoPostProc)


if __name__ == '__main__':
    pass
