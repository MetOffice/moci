#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

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
    def process_types(self):
        '''
        Return a list of tuples controlling the processing (creation/archive)
        of files other than restarts and means.
           (<type str> method_name, <type bool>)
        '''
        return [('concat_daily_means', self.naml.processing.cat_daily_means)]

    def rst_set_stencil(self, rsttype):
        '''
        Return a regular expression to match means filenames output
        directly by the model.
        '''
        return \
            r'^{P}i\.restart{T}\.\d{{4}}-[-\d]*(\.nc)?$'.format(P=self.prefix,
                                                                T=rsttype)

    def general_mean_stencil(self, field, base=None):
        '''
        Return a regular expression to match means filenames output
        directly by the model.
        '''
        return \
            r'^{P}i\.({B}\.\d{{4}}-\d{{2}}(-\d{{2}})?(-\d{{2}})?{M}).nc$'.\
            format(P=self.prefix,
                   B=base if base else r'\d+[hdsy]',
                   M='' if base else r'|1m.\d{4}-\d{2}')

    def move_to_share(self, pattern=None):
        '''
        CICE code differentiates daily data from monthly data only in the
        date format (not the frequency stamp - this relates to resubmit period):
            YYYY-MM.nc = monthly data
            YYYY-MM-DD.nc = daily data
        Pre-pend ModelTemplate.move_to_share with a forced renaming of
        "1d.YYYY-MM.nc" files to "1m.YYYY-MM.nc
        '''
        monthly_1d = utils.get_subset(
            self.work,
            r'^{}i\.1d\.\d{{4}}-\d{{2}}\.nc$'.format(self.prefix)
            )
        for fname in monthly_1d:
            newfname = os.path.join(self.work, fname.replace('.1d.', '.1m.'))
            os.rename(os.path.join(self.work, fname), newfname)
        super(CicePostProc, self).move_to_share(pattern=pattern)

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
    def create_concat_daily_means(self):
        '''
        Concatenate daily mean data into a single file.
        Hourly files dated YYYY-M1-02 to YYYY-M2-01 are included in the month.
        Daily files dated YYYY-MM-01 to YYYY-MM-DEnd are included in the month.
        '''
        ncf = netcdf_filenames.NCFilename('cice',
                                          self.suite.prefix,
                                          self.model_realm,
                                          base='1d')

        patt = r'^{P}i\.[0-9hdm]*_?24h\.{{Y}}-{{M}}-{{D}}(-\d{{{{5}}}})?\.nc$'.\
            format(P=self.suite.prefix)
        if self.work != self.share:
            self.move_to_share(pattern=patt.format(Y=r'\d{4}', M=r'\d{2}',
                                                   D=r'\d{2}'))

        endfiles = utils.get_subset(self.share,
                                    patt.format(Y=r'\d{4}', M=r'\d{2}', D='01'))
        if endfiles:
            raw_output = True
        else:
           # Try again with convention compliant files with base=1d
            raw_output = False
            endfiles = utils.get_subset(self.share, self.end_stencil('1m', ncf))
            # Filter out files with period greater than 1d.
            # 2d is expected because CICE raw data is not cf-compliant,
            # and allowance is made for this in datestamp_period()
            endfiles = [f for f in endfiles if self.datestamp_period(f) == '2d']

        for end in endfiles:
            if raw_output:
                # Using raw output (24 hourly files)
                # Set ncf.start_date to the start of the period.
                # `base=2m` is required since get_date() usually expects the
                # filename enddate to be the last day of the previous month and
                # adjusts accordingly.
                ncf.start_date = self.get_date(end, base='2m')
                catfiles = [end]
                catfiles += utils.get_subset(
                    self.share,
                    patt.format(Y=ncf.start_date[0], M=ncf.start_date[1],
                                D=r'(0[2-9]|[1-3][0-9])')
                    )

            else:
                # Daily mean files - netCDF filename convention files
                ncf.start_date = self.get_date(end)
                catfiles = utils.get_subset(self.share,
                                            self.set_stencil('1m', ncf))
                # Adjust ncf.start_date back to the start of the period for
                # file renaming purposes
                ncf.start_date = [
                    str(d).zfill(2) for d in utils.add_period_to_date(
                        self.get_date(end, enddate=True), '-m'
                        )[:3]
                    ]

            if len(catfiles) == self.suite.monthlength(ncf.start_date[1]):
                catfiles = utils.add_path(catfiles, self.share)
                outfile = os.path.join(self.share, 'cicecat')
                icode = self.suite.preprocess_file('ncrcat', sorted(catfiles),
                                                   outfile=outfile)
                if icode == 0:
                    utils.remove_files(catfiles)
                    # Rename file according to netCDF convention
                    ncf.rename_ncf(outfile, target='1m')

            else:
                msg = 'concat_daily_means: Cannot create month of daily means '
                msg += 'as only got {} files:\n{}'.format(len(catfiles),
                                                          catfiles)
                utils.log_msg(msg, level='ERROR')

    @timer.run_timer
    def archive_concat_daily_means(self):
        ''' Archive concatenated daily mean data '''

        to_archive = utils.get_subset(self.share,
                                      r'cice_{}{}_1d_\d{{8}}-\d{{8}}\.nc'.
                                      format(self.suite.prefix.lower(),
                                             self.model_realm))
        if to_archive:
            arch_files = self.archive_files(to_archive)

            self.clean_archived_files(arch_files,
                                      'CICE concatenated daily means')
        else:
            utils.log_msg(' -> Nothing to archive')


INSTANCE = ('nemocicepp.nl', CicePostProc)


if __name__ == '__main__':
    pass
