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
    cice.py

DESCRIPTION
    Class definition for CicePostProc - holds CICE model properties
    and methods
'''
import re
import os

import modeltemplate as mt
import timer
import utils
import netcdf_filenames


class CicePostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the CICE post processing application.
    '''
    @property
    def set_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) set

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        set_stencil = super(CicePostProc, self).set_stencil
        set_stencil[mt.RR] = lambda rsttype: \
            r'^{P}i\.restart{T}\.\d{{4}}-[-\d]*(\.nc)?$'.\
            format(P=self.prefix, T=rsttype)
        return set_stencil

    @property
    def mean_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) mean.

        XX stencil for '1m' with no base is defined separately because the
        Gregorian calendar model produces daily component files in addition to
        a complete monthly file.
        These are are not required for creating higher means.
        '''
        mean_stencil = super(CicePostProc, self).mean_stencil
        mean_stencil[mt.XX] = lambda field, base=None: \
            r'^{P}i\.({B}\.\d{{4}}-\d{{2}}(-\d{{2}})?(-\d{{2}})?{M}).nc$'.\
            format(P=self.prefix,
                   B=base if base else r'\d+[hdsy]',
                   M='' if base else r'|1m.\d{4}-\d{2}')

        return mean_stencil

    @property
    def model_components(self):
        '''Name of model component, to be used as a prefix to archived files '''
        return {'cice': ''}

    @property
    def model_realm(self):
        ''' Return the standard realm ID character for the model: i=ice '''
        return 'i'

    @property
    def cfcompliant_output(self):
        '''
        Return "True" if the raw model output datestamp is CF-compliant.
        CICE produces a single datestamp which is NOT CF-compliant.
        '''
        return False

    @property
    def rsttypes(self):
        ''' Returns a tuple of restart file types available '''
        return ('', r'.age')

    @property
    def archive_types(self):
        '''
        Additional archiving methods to call for files
        other than restarts and means.
        Returns a list of tuples: (method_name, bool)
        '''
        return [('concat_daily_means', self.naml.cat_daily_means)]

    def get_date(self, fname, enddate=False, base=None):
        '''
        Returns the date extracted from the filename provided.
        By default, the start date for the data is returned

        Keyword argument `base` is required only if filename format does
        not meet the Met Office convention.
        '''
        rtndate = netcdf_filenames.ncf_getdate(fname, enddate=enddate)
        if not rtndate:
            # Filename datestamp is of the direct CICE output format
            datestrings = re.findall(r'\d{4}-\d{2}-\d{2}-\d{2}\.|'
                                     r'\d{4}-\d{2}-\d{2}|\d{4}-\d{2}', fname)
            if len(datestrings) == 0:
                utils.log_msg('Unable to get date for file:\n\t' + fname,
                              level='WARN')
                rtndate = [None]*3

            else:
                rtndate = datestrings[-1].strip('.').split('-')
                if len(rtndate) == 2:
                    rtndate.append(str(self.suite.monthlength(rtndate[1]))
                                   if enddate else '01')

                if 'restart' in fname:
                    # No change required.
                    pass
                elif not enddate:
                    digits, char = re.match(r'(\d+)(\w+)', base if base else
                                            fname.split('.')[1]).groups()

                    freq = '-' + str(int(digits) - 1) + char
                    indate = ['00']*5
                    for i, val in enumerate(rtndate):
                        indate[i] = val
                    outdate = utils.add_period_to_date(indate, freq)
                    rtndate = [str(i).zfill(2) for i in outdate[0:len(rtndate)]]

        return tuple(rtndate)

    @timer.run_timer
    def archive_concat_daily_means(self):
        '''
        Concatenate daily mean data into a single file.
        Files dated YYYY-M1-01 to YYYY-M2-01 are included in a monthly file.
        '''
        patt = r'^{P}i\.[0-9d_]*24h\.{{Y}}-{{M}}-{{D}}(-\d{{{{5}}}})?\.nc$'.\
            format(P=self.suite.prefix)
        if self.work != self.share:
            self.move_to_share(pattern=patt.format(Y=r'\d{4}', M=r'\d{2}',
                                                   D=r'\d{2}'))

        endset = utils.get_subset(self.share,
                                  patt.format(Y=r'\d{4}', M=r'\d{2}', D='01'))
        for end in endset:
            catfiles = [end]
            # `base=2m` as get_date() usually expects the enddate in filename
            # to be the last day of the previous month and adjusts accordingly.
            startdate = self.get_date(end, base='2m')
            catfiles += utils.get_subset(self.share,
                                         patt.format(Y=startdate[0],
                                                     M=startdate[1],
                                                     D=r'(0[2-9]|[1-3][0-9])'))

            if len(catfiles) == 30:
                catfiles = utils.add_path(catfiles, self.share)
                outfile = os.path.join(self.share, 'cicecat')
                icode = self.suite.preprocess_file('ncrcat', sorted(catfiles),
                                                   outfile=outfile)
                if icode == 0:
                    utils.remove_files(catfiles)
                    ncfname = netcdf_filenames.NCFilename(
                        'cice', self.suite.prefix, self.model_realm,
                        base='1d', start_date=startdate
                        )
                    # Rename file according to netCDF convention
                    ncfname.rename_ncf(outfile, target='1m')

            else:
                msg = 'concat_daily_means: Cannot create month of daily means '
                msg += 'as only got {} files:\n{}'.format(len(catfiles),
                                                          catfiles)
                utils.log_msg(msg, level='ERROR')

        to_archive = utils.get_subset(self.share,
                                      r'cice_{}{}_1d_\d{{8}}-\d{{8}}\.nc'.
                                      format(self.suite.prefix.lower(),
                                             self.model_realm))
        if to_archive:
            arch_files = self.archive_files(to_archive)
            del_files = [fn for fn in arch_files if arch_files[fn] != 'FAILED']
            if del_files:
                msg = 'Deleting archived files: \n\t' + '\n\t'.join(to_archive)
                utils.log_msg(msg)

                if utils.get_debugmode():
                    # Append "ARCHIVED" suffix to files, rather than deleting
                    for fname in del_files:
                        fname = os.path.join(self.share, fname)
                        os.rename(fname, fname + '_ARCHIVED')
                else:
                    utils.remove_files(del_files, path=self.share)
        else:
            utils.log_msg(' -> Nothing to archive')


INSTANCE = ('nemocicepp.nl', CicePostProc)


if __name__ == '__main__':
    pass
