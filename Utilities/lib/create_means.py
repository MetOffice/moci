#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    create_means.py

DESCRIPTION
    Download monthly means (a.pm files) from MASS and mean them to make
    seasonal and annual means using to Met Office Fortran executable: ppmnvar

    Method:
        At the end of each November, download the last year of monthly means.
        Make seasonal means and then annual mean out of these.
        Missing files will result in an error except in the event that the
        "current" cycle time is found to be too close to the "initial" cycle
        time - in which case all possible means are created.

REQUIRED ENVIRONMENT:
    JOBID       - Filename prefix to 'a' realm ID. Ususally 5-char.
    ARCHIVE_SET - Target dataset, located in moose:crum.
    MEANS       - Space separated list of 3-char seasons (e.g. djf mam jja)
                  or 4-digit (MMDD) years.
    BASIS       - 8-digit string representing YYYYMMDD: experiment basis time.
                  Longer strings (e.g. ISO-format date) are acceptable,  but
                  only the first 8 digits will be interpreted.
    TCYCLE      - ISO-format date string representing current cycle time.
    NCYCLE      - ISO format date string representing end of current cycle.
    SCRATCH     - Working directory.

OPTIONAL ENVIRONMENT:
    REAL_YEAR_INCLUSIVE - Default value=true
                  Select fields with T2 from midnight 12/01 in the previous year
                  to midnight 12/01 in the current year inclusive. 
                  When false, Only fields with T2 in the current year will be
                  selected.  This should be the case for means produced by the
                  UM climate meaning system.
    PPMEANVAR   - Path to the ppmeanvar run script.  
                  Default value='/opt/ukmo/utils/bin/run_ppmnvar'
'''

import os
import re
import subprocess
import shutil

_COMPONENTS = {}
_COMPONENTS['djf'] = ['dec', 'jan', 'feb']
_COMPONENTS['mam'] = ['mar', 'apr', 'may']
_COMPONENTS['jja'] = ['jun', 'jul', 'aug']
_COMPONENTS['son'] = ['sep', 'oct', 'nov']
_COMPONENTS['1201'] = ['djf', 'mam', 'jja', 'son']

_YEAR_STR = '1201'

class UMFileError(Exception):
    ''' UMFile exception class '''
    pass


class UMFile(object):
    '''Class to handle UM files'''

    _moose = 'moose:/crum'
    _years = [_YEAR_STR]
    _seasons = 'ndjfmamjjasond'
    _months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
               'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

    def __init__(self, archive_set, jobid, year, period):
        '''
        Arguments:
           archive_set - <type 'str'> Dataset in moose:crum
           jobid       - <type 'str'> Filename prefix ($RUNID)
           year        - <type 'int'> Start year of annual mean period
           period      - <type 'str'> Requested period of mean
        '''
        self.archive_set = archive_set
        self.jobid = jobid
        self.year = year
        self.period = period
        self.moose = '{0._moose}/{0.archive_set}'.format(self)

    @property
    def id5(self):
        '''Set str to be last 5 characters of jobid'''
        return self.jobid[-5:]

    def streamcode(self, period):
        '''Return MASS stream used for appropriate period'''
        if period in self._years:
            stream = 'y'
        elif period in self._seasons:
            stream = 's'
        elif period in self._months:
            stream = 'm'
        return stream

    def url_collection(self, period=None):
        ''' Generate a collection for the period mean '''
        try:
            streamcode = self.streamcode(period)
        except TypeError:
            streamcode = self.streamcode(self.period)

        template = '{0.moose}/ap{1!s}.pp'
        return template.format(self, streamcode)

    def get_file(self, year, period):
        ''' Generate a um file name '''
        streamcode = self.streamcode(period)
        template = '{0.id5}a.p{1!s}{2!s}{3!s}.pp'
        return template.format(self, streamcode, year, period)

    def generate_files(self):
        '''
        Return list of source filenames for this period, using
        _COMPONENTS dictionary.
        Where December is a component, use previous year.
        '''
        year = self.year
        fnames = []
        for cmpt in _COMPONENTS[self.period]:
            if cmpt == 'dec':
                year = self.year - 1
            else:
                year = self.year
            fnames.append(self.get_file(year, cmpt))
        return fnames

    def source_url(self):
        '''
        Return the collection url for the source files.
        Use the first component to determine whether stream is month, season etc
        '''
        cmpt = _COMPONENTS[self.period][0]
        return self.url_collection(period=cmpt)


class ArchiveError(Exception):
    ''' Archive exception class '''
    pass


class Archive(object):
    ''' Class to define Moose archiving methods '''
    def __init__(self, listfiles, target):
        '''
        Arguments:
            listfiles - <type 'list'> List of files to archive/retrieve
            target    - <type 'str'> Target path for archived/retrieved files
        '''
        self._files = listfiles
        self._url = target

    @property
    def _strfiles(self):
        ''' Returin a space separated list of files '''
        return ' '.join(self._files)

    @property
    def _prtfiles(self):
        ''' Return a carriage return separated list of files for printing '''
        return '\n'.join(self._files)

    def arch_cmd(self, moocmd):
        '''
        Generate moo command
        Argument: moocmd - One of 'put' or 'get'
        '''
        template = 'moo {1} -f {0._strfiles} {0._url}'
        return template.format(self, moocmd)

    def print_msg(self, moocmd):
        ''' Print informative message '''
        template = '[INFO] {1} the following files to {0._url}\n\t{0._prtfiles}'
        print(template.format(self, moocmd))

    def put_files(self):
        ''' Upload files to Moose '''
        print(self.print_msg('Archiving'))
        try:
            _ = subprocess.check_output(self.arch_cmd('put').split())
        except subprocess.CalledProcessError as exc:
            print('Error archiving files to MASS-R')
            print('Return code = {0}'.format(exc.returncode))
            raise ArchiveError('Error archiving file to MASS')

    def get_files(self):
        ''' Download files from Moose '''
        print(self.print_msg('Retrieving'))
        try:
            _ = subprocess.check_output(self.arch_cmd('get').split())
        except subprocess.CalledProcessError as exc:
            print('Error retrieving files from MASS-R')
            print('Return code = {0}'.format(exc.returncode))
            raise ArchiveError('Error retrieving files from MASS')

    def select_year(self, year, user_error_ok=True):
        '''
        Extract a single year of files from MASS

        This gets anything which starts (T1) in or after December in
        the previous year, and ends before the start of December,
        assuming that fields 'hear' an interval [T1, T2). Using yrd
        doesn't work because there can be fields where both T1 and T2
        are in the previous December: it is worth checking for these
        as they could indicate a problem, although some TRIFFID
        requests seem to have a T2 at the start of the last timestep
        in the month (23:40 with 20-minute timesteps) which is an
        artifact of their sampling interval.

        If user_error_ok is true (default) then this will simply note
        on user error.
        '''
        queryfile = 'year.qry'
        with open(queryfile, 'w') as qfile:
            qfile.write('begin\n')
            if os.getenv('REAL_YEAR_INCLUSIVE', 'true').lower() == 'true':
                qfile.write(' T1 >= {{{0!s}/12/01 00:00:00}}\n'.format(year - 1))
                qfile.write(' T2 <= {{{0!s}/12/01 00:00:00}}\n'.format(year))
            else:
                qfile.write(' yrd = {0!s}\n'.format(year))
            qfile.write('end\n')

        self.print_msg('Retrieving')
        cmd = 'moo select {1} -f {0._strfiles} {0._url}'.format(self, queryfile)
        try:
            _ = subprocess.check_output(cmd.split())
            restored_files = [f for f in os.listdir('.') if '.pp' in f]
            print('[INFO] Restored files:\n\t' + '\n\t'.join(restored_files))
        except subprocess.CalledProcessError as exc:
            if user_error_ok and exc.returncode == 2:
                print('[WARN] No files found')
            else:
                print('[ERROR] Error retrieving files from MASS-R.')
                print('[ERROR] Return code = {0}'.format(exc.returncode))
                raise ArchiveError('Error retrieving files from MASS')

        os.remove(queryfile)


class PPMeanVarError(Exception):
    ''' PPMeanVar exception class '''
    pass


class FileMissingError(Exception):
    ''' FileMissing exception class '''
    pass


class PPMeanVar(object):
    '''
    Class to define methods for use with the ppmeanvar Fortran executable.
    '''

    _exec = os.getenv('PPMEANVAR', '/opt/ukmo/utils/bin/run_ppmnvar')
    _listfile = 'ppmnvar.list'

    def __init__(self, infiles, meanfile):
        '''
        Arguments:
            infiles  - <type 'list'> Component files
            meanfile - <type 'str'> Output mean file name
        '''
        self._files = infiles
        self._mean = meanfile
        print('[INFO] Using ppmeanvar from: ' + self._exec)

    @property
    def _prtfiles(self):
        ''' Return a carriage-return separated list of files for printing '''
        return '\n'.join(self._files)

    def mean(self):
        ''' Create the mean file '''
        print('Making mean {0._mean} from:\n{0._prtfiles}'.format(self))

        # Populate input file for ppmnvar
        with open(self._listfile, 'w') as outf:
            lastfile = self._files[-1]
            for infile in self._files:
                outf.write(infile)
                if infile == lastfile:
                    outf.write(' {0._mean}'.format(self))
                outf.write('\n')

        # Call run_ppmnvar
        cmd = '{0._exec} -F {0._listfile}'.format(self)
        try:
            _ = subprocess.check_output(cmd.split())
        except subprocess.CalledProcessError as exc:
            raise PPMeanVarError('Error meaning files ({0})'.\
                                     format(exc.returncode))

        os.remove(self._listfile)


class MakeMean(object):
    ''' Class containing methods for creating a mean file '''
    _worktemp = 'mkmean_{0}_{1!s}'

    def __init__(self, workdir, archive_set, jobid, year, means):
        '''
        Arguments:
           workdir     - <type 'str'> working directory
           archive_set - <type 'str'> Dataset in moose:crum
           jobid       - <type 'str'> Filename prefix ($RUNID)
           year        - <type 'int'> Start year of annual mean period
           means       - <type 'list'> List of means required
        '''
        tempdir = self._worktemp.format(jobid, year)
        self._workdir = os.path.join(workdir, tempdir)
        self._archive_set = archive_set
        self._jobid = jobid
        self._year = year
        self._means = means

    def _mkcwd(self):
        ''' Create and enter the working directory '''
        # Remove directory if it exists
        if os.path.exists(self._workdir):
            shutil.rmtree(self._workdir)
        # Create directory
        os.makedirs(self._workdir)
        # Enter directory
        os.chdir(self._workdir)

    def _mkmean(self, period):
        ''' Create required mean '''
        # Create object to generate UM source file names
        try:
            umfiles = UMFile(self._archive_set,
                             self._jobid,
                             self._year,
                             period)
        except UMFileError:
            raise

        # Make a mean using ppmnvar
        arch_files = []
        try:
            filearray = umfiles.generate_files()
            meanfile = umfiles.get_file(self._year, period)
            # check whether all the input files exist and skip if not
            if all_files_exist(filearray):
                PPMeanVar(filearray, meanfile).mean()
                arch_files.append(meanfile)
            else:
                if self.spinup(filearray):
                    print('[INFO] Too close to BASIS time to create mean: ' +
                          meanfile.rstrip('.p'))
                else:
                    raise FileMissingError(
                        'Input files missing for ' + meanfile
                        )
        except PPMeanVarError:
            raise

        if arch_files:
            # Archive the means to MASS
            try:
                Archive(arch_files, umfiles.url_collection()).put_files()
            except ArchiveError:
                raise

    def spinup(self, filearray):
        '''
        Return True if the current cycle time is too close to the $BASIS
        for sufficient files to be available to create the mean.
        '''
        basis = map(int, re.match(r'^(\d{4})(\d{2})(\d{2})',
                                  os.environ['BASIS']).groups())
        mths = [None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        ssns = [None]*13
        ssns[3] = 'mam'
        ssns[6] = 'jja'
        ssns[9] = 'son'
        ssns[12] = 'djf'

        spinup = []
        for fname in filearray:
            year, month = re.match(r'.*a\.p\w(\d{4})(\w{3})',
                                   fname).groups()
            if month == 'djf':
                year = int(year) - 1
            if int(year) < basis[0]:
                spinup.append(True)
            elif int(year) == basis[0]:
                try:
                    spinup.append(mths.index(month) < basis[1])
                except ValueError:
                    spinup.append(ssns.index(month) < basis[1])
        return any(spinup)

    def means(self):
        ''' Create all requested means '''
        # Create and enter working directory
        self._mkcwd()

        # Restore 1 year of monthly means from MASS
        umfiles = UMFile(self._archive_set,
                         self._jobid,
                         self._year,
                         self._means[0])
        try:
            stream = umfiles.source_url()
            Archive([stream], '.').select_year(self._year)
        except ArchiveError:
            raise

        # Loop over requested periods creating means.
        for period in self._means:
            self._mkmean(period)

        # Tidy up
        shutil.rmtree(self._workdir)


def all_files_exist(filearray):
    '''
    Test the existence of a list of files, and return true if all present.
    Else false.
    '''
    return all([os.path.isfile(fname) for fname in filearray])


class DecDate(object):
    ''' Class to define methods relating to the cycle time '''
    _dec_temp = '{0!s:4s}1201T0000Z'

    def __init__(self, datec):
        '''
        Arguments
            datec: ISO-format date string representing the current cycle time
        '''
        self._datec = str(datec)

    @property
    def year(self):
        ''' Return an integer representing the year '''
        return int(self._datec[0:4])

    @property
    def dec_year(self):
        ''' Return an ISO-format date string for 0Z Dec 1st '''
        return self._dec_temp.format(self.year)

    @property
    def dec_after(self):
        '''
        Return an integer representing the year at the end
        of the annual mean period covering the current time.
        '''
        datec_yr = self.year
        if self.dec_year < self._datec:
            datec_yr += 1
        return datec_yr

    @property
    def dec_before(self):
        '''
        Return an integer representing the year at the beginning
        of the annual mean period covering the current time.
        '''
        datec_yr = self.year
        if self._datec < self.dec_year:
            datec_yr -= 1
        return datec_yr


def main():
    '''  Main function '''

    workdir = os.environ['SCRATCH']
    jobid = os.environ['JOBID']
    archive_set = os.environ['ARCHIVE_SET']
    tcycle = os.environ['TCYCLE']
    ncycle = os.environ['NCYCLE']
    means = re.split('[ ,]', os.environ['MEANS'])

    # Reverse sort the list to ensure the annual mean (4-digit string) list the
    # last in the list because it depends on seasonal means being created first
    means = sorted(means, reverse=True)

    # Calculate year of last 0Z 1st December before current model time
    cycle_yr = DecDate(ncycle).dec_before

    # Run after the 1st December. The model must have passed midnight on 1st
    # December in order for the November file to be finalised and archived. In
    # practice this normally means it will run at the end of the December cycle
    # (or the Oct-Dec cycle for 3-month cycles).
    # We assume here that cycle is not longer than a year, so at most
    # one December is passed.
    if tcycle <= DecDate(cycle_yr).dec_year < ncycle:
        print('[INFO] Making seasonal and annual means for ' + str(cycle_yr))

        mkmean = MakeMean(workdir, archive_set, jobid, cycle_yr, means)
        mkmean.means()
    else:
        print('[INFO] No means to make during this cycle')


if __name__ == '__main__':
    main()

