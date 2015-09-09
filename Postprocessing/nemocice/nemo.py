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
    nemo.py

DESCRIPTION
    Class definition for NemoPostProc - holds NEMO model properties
    and methods
'''
import os
import re

from collections import OrderedDict

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
    def set_stencil(self):
        return {
            mt.RR: lambda y, m, s, f: '^{}o_\d{{8}}_restart{}\.nc$'.
            format(self.prefix, f),
            mt.MM: lambda y, m, s, f: '^{}o_10d_\d{{8}}_{}{}\d{{2}}_{}\.nc$'.
            format(self.prefix, y, m, f),
            mt.SS: lambda y, m, s, f:
            '^{}o_1m_({}{}|{}{}|{}{})01_\d{{8}}_{}\.nc$'.
            format(self.prefix,
                   y if type(s[3]) != int else str(int(y) - s[3]),
                   s[0], y, s[1], y, s[2], f),
            mt.AA: lambda y, m, s, f: '^{}o_1s_\d{{8}}_{}\d{{2}}30_{}\.nc$'.
            format(self.prefix, y, f),
        }

    @property
    def end_stencil(self):
        return {
            mt.RR: None,
            mt.MM: lambda s, f: '^{}o_10d_\d{{6}}21_\d{{6}}30_{}\.nc$'.
            format(self.prefix, f),
            mt.SS: lambda s, f: '^{}o_1m_\d{{4}}{}01_\d{{8}}_{}\.nc$'.
            format(self.prefix, s[2], f),
            mt.AA: lambda s, f: '^{}o_1s_\d{{4}}0901_\d{{8}}_{}\.nc$'.
            format(self.prefix, f),
        }

    @property
    def mean_stencil(self):
        return {
            mt.MM: lambda y, m, s, f: '{}o_1m_{}{}01_{}{}30_{}.nc'.
            format(self.prefix, y, m, y, m, f),
            mt.SS: lambda y, m, s, f: '{}o_1s_{}{}01_{}{}30_{}.nc'.
            format(self.prefix,
                   y if type(s[3]) != int else str(int(y) - s[3]),
                   s[0], y, s[2], f),
            mt.AA: lambda y, m, s, f: '{}o_1y_{}1201_{}1130_{}.nc'.
            format(self.prefix, y if '*' in y else (int(y)-1), y, f),
        }

    @property
    def rebuild_cmd(self):
        return self.nl.exec_rebuild

    def buffer_rebuild(self, filetype):
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
        utils.log_msg('Unable to get date for file:\n\t' + fname, 3)

    def rebuild_restarts(self):
        self.rebuild_fileset(self.share, 'restart')

    def rebuild_means(self):
        for field in self.fields:
            self.rebuild_fileset(self.share, field, rebuildall=True)

    def rebuild_fileset(self, datadir, filetype, rebuildall=False):
        SUFFIX = '0000.nc'
        bldfiles = utils.get_subset(datadir,
                                    '^.*{}.*{}$'.format(filetype, SUFFIX))
        buff = self.buffer_rebuild('rst') if \
            'restart' in filetype else self.buffer_rebuild('mean')
        rebuild_required = len(bldfiles) > buff
        while len(bldfiles) > buff:
            bldfile = bldfiles.pop(0)
            corename = bldfile.split('_'+SUFFIX)[0]
            bldset = utils.get_subset(datadir, '^{}.*\.nc$'.format(corename))

            year = month = day = None
            for part in reversed(corename.split(filetype)):
                if re.search('_\d{8}_', part):
                    year, month, day = self.get_date(part)
                    break

            if rebuildall or self.timestamps(month, day, process='rebuild'):
                icode = self.rebuild_namelist(datadir, corename,
                                              len(bldset), omp=1)
            else:
                msg = 'Only rebuilding periodic files: ' + \
                    str(self.nl.rebuild_timestamps)
                utils.log_msg(msg)
                icode = 0

            if icode == 0:
                filename = os.path.join(datadir, corename + '.nc')
                if os.path.isfile(filename):
                    self.check_fileformat(filename, year, month, day, filetype)

                if not self.suite.finalcycle:
                    utils.log_msg('Deleting component files for: ' + corename)
                    utils.remove_files(bldset, self.share)

        if bldfiles and not rebuild_required:
            msg = 'Nothing to rebuild - {} {} files available ' \
                '({} retained).'.format(len(bldfiles), filetype, buff)
            utils.log_msg(msg)

    def rebuild_namelist(self, datadir, filebase, ndom,
                         omp=16, chunk=None, dims=None):
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
            icode, _ = utils.exec_subproc(
                'cd {}; {}'.format(datadir, self.rebuild_cmd))
            if icode == 0 and \
                    os.path.isfile(os.path.join(datadir, filebase + '.nc')):
                utils.log_msg('Successfully rebuilt file:' + filebase, 2)
                utils.remove_files(namelistfile)
            else:
                utils.log_msg('{}: Error={}'.format(self.rebuild_cmd, icode), 4)
                utils.log_msg(' -> Failed to rebuild file:' + filebase, 4)
                utils.catch_failure(self.nl.debug)
        else:
            utils.log_msg('Failed to create namelist file:' + namelist, 3)
            icode = 999
        return icode

    def check_fileformat(self, inputfile, year, month, day, filetype):
        '''
        Output file format changed at vn3.5.
        This function renames rebuilt files with the original format
        '''
        if 'restart' in filetype:
            field = ''
            period = mt.RR
            template = '{}o_{}{}{}_restart.nc'.format(self.prefix,
                                                      year, month, day)
        else:
            field = filetype
            period = mt.MM
            template = '{0}o_10d_{1}{2}{3}_{1}{2}{4:0>2d}_{5}.nc'.\
                format(self.prefix, year, month, day, int(day)+9, field)

            args = ('\d{4}', '\d{2}', None, field)
            if not re.match(self.set_stencil[period](*args),
                            os.path.basename(inputfile)):
                os.rename(inputfile, os.path.join(self.share, template))


INSTANCE = ('nemocicepp.nl', NemoPostProc)


if __name__ == '__main__':
    pass
