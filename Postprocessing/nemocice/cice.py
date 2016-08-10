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
        return {
            mt.RR: lambda y, m, s, f:
                   r'^{P}i\.restart{F}\.\d{{4}}-[-\d]*(\.nc)?$'.
                   format(P=self.prefix, F=f),
            mt.MM: lambda y, m, s, f: r'^{P}i\.{B}\.{Y}-{M}-\d{{2}}\.nc$'.
                   format(P=self.prefix, B=self.month_base, Y=y, M=m),
            mt.SS: lambda y, m, s, f:
                   r'^{P}i\.1m\.({Y1}-{M1}|{Y2}-{M2}|{Y2}-{M3})\.nc$'.
                   format(P=self.prefix,
                          Y1=int(y) - s[3] if isinstance(s[3], int) else y,
                          Y2=y,
                          M1=s[0],
                          M2=s[1],
                          M3=s[2]),
            mt.AA: lambda y, m, s, f:
                   r'^{P}i\.1s\.\d{{4}}-\d{{2}}_{Y}-\d{{2}}\.nc$'.
                   format(P=self.prefix, Y=y),
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
                   r'^{P}i\.{B}\.\d{{4}}-\d{{2}}-(28|29|30|31)\.nc$'.
                   format(P=self.prefix, B=self.month_base),
            mt.SS: lambda s, f: r'^{P}i\.1m\.\d{{4}}-{M}\.nc$'.
                   format(P=self.prefix, M=s[2]),
            mt.AA: lambda s, f: r'^{P}i\.1s\.\d{{4}}-\d{{2}}_\d{{4}}-11\.nc$'.
                   format(P=self.prefix),
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
                   r'^{P}i\.{B}\.\d{{4}}-\d{{2}}(-\d{{2}})?(-\d{{2}})?\.nc$'.
                   format(P=self.prefix, B=y if y else r'\d+[hdmsy]'),
            mt.MM: lambda y, m, s, f: r'{P}i.1m.{Y}-{M}.nc'.
                   format(P=self.prefix, Y=y, M=m),
            mt.SS: lambda y, m, s, f: r'{P}i.1s.{Y1}-{M1}_{Y2}-{M2}.nc'.
                   format(P=self.prefix,
                          Y1=int(y) - s[3] if isinstance(s[3], int) else y,
                          Y2=y,
                          M1=s[0],
                          M2=s[2]),
            mt.AA: lambda y, m, s, f: r'{P}i.1y.{Y1}-12_{Y2}-11.nc'.
                   format(P=self.prefix,
                          Y1=y if '*' in y else (int(y)-1),
                          Y2=y),

        }

    @property
    def rsttypes(self):
        return ('', r'.age')

    @property
    def archive_types(self):
        '''
        Additional archiving methods to call for files
        other than restarts and means.
        Returns a list of tuples: (method_name, bool)
        '''
        return [('concat_daily_means', self.nl.cat_daily_means),]

    def get_date(self, fname, startdate=True):
        '''
        Returns the date extracted from the filename provided.
        By default, the start date for the data is returned
        '''
        datestrings = re.findall(r'\d{4}-\d{2}-\d{2}|\d{4}-\d{2}', fname)
        if len(datestrings) == 0:
            utils.log_msg('Unable to get date for file:\n\t' + fname, level=3)
            return (None,)*3

        date = datestrings[0 if startdate else -1].split('-')
        day = date[2] if len(date) == 3 else None

        return date[0], date[1], day

    @timer.run_timer
    def archive_concat_daily_means(self):
        '''Concatenate daily mean data into a single file'''
        in_pat = r'^{P}i\.[0-9d_]*24h\.{{Y}}-{{M}}-{{D}}(-\d{{{{5}}}})?\.nc$'.\
            format(P=self.suite.prefix)
        out_pat = r'{P}i_1d_{{Y1}}{{M1}}01-{{Y2}}{{M2}}01.nc'.\
            format(P=self.suite.prefix)

        if self.work != self.share:
            self.move_to_share(pattern=in_pat.format(Y=r'\d{4}', M=r'\d{2}',
                                                     D=r'\d{2}'))

        endset = utils.get_subset(self.share, in_pat.format(Y=r'\d{4}',
                                                            M=r'\d{2}',
                                                            D='01'))
        for end in endset:
            catfiles = [end]
            end_yr, end_mo, _ = self.get_date(end)
            if end_mo == '01':
                start_yr = str(int(end_yr)- 1)
                start_mo = '12'
            else:
                start_yr = end_yr
                start_mo = str(int(end_mo) - 1).zfill(2)
            catfiles += utils.get_subset(
                self.share,
                in_pat.format(Y=start_yr, M=start_mo,
                              D=r'(0[2-9]|[1-3][0-9])')
                )
            if len(catfiles) != 30:
                msg = 'concat_daily_means: Cannot create month of daily means '
                msg += 'as only got {} files:\n{}'.format(len(catfiles),
                                                          catfiles)
                utils.log_msg(msg, level=5)
            catfiles = utils.add_path(catfiles, self.share)

            outfile = out_pat.format(Y1=start_yr, Y2=end_yr,
                                     M1=start_mo, M2=end_mo)
            outfile = os.path.join(self.share, outfile)
            self.suite.preprocess_file('ncrcat', sorted(catfiles),
                                       outfile=outfile)
            utils.remove_files(catfiles)

        to_archive = utils.get_subset(self.share,
                                      out_pat.format(Y1=r'\d{4}', Y2=r'\d{4}',
                                                     M1=r'\d{2}', M2=r'\d{2}'))
        if to_archive:
            arch_files = self.archive_files(to_archive)
            if not [fn for fn in arch_files if arch_files[fn] == 'FAILED']:
                msg = 'Deleting archived files: \n\t' + '\n\t'.join(to_archive)
                utils.log_msg(msg)
                utils.remove_files(to_archive, self.share)
        else:
            utils.log_msg(' -> Nothing to archive')


INSTANCE = ('nemocicepp.nl', CicePostProc)


if __name__ == '__main__':
    pass
