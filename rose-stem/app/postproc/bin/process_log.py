#!/usr/bin/env python2.7
import os
import re

logfile = os.environ['CYLC_TASK_LOG_ROOT'] + '-archive.log'
cylclog = os.environ['CYLC_SUITE_SHARE_DIR'] + '/cylclog'
archive_set = os.environ['ARCHIVE_SET']

print '*******************************************************************'
print '[POST-SCRIPT] Processing the archive logs for verification purposes'
print '              Processing postproc logfile:', logfile
print '              Writing to Moose logfile:', cylclog
print '*******************************************************************'

dataset = {}
try:
    for line in open(logfile, 'r').readlines():
        fname = os.path.basename(line.split()[0])
        collection = ''
        if ('WOULD BE ARCHIVED' in line) and '_ARCHIVED' not in line:
            if re.match(r'.*a\.da.*', fname):
                # Atmos dump file
                collection = 'ada.file'
            elif re.match(r'.*a\.([pm])([a-z0-9]).*', line):
                # Atmos pp/fields files
                filetype, stream = re.match(r'.*a\.([pm])([a-z0-9])\d{4}.*', line).groups()
                version = 'pp' if fname.endswith('.pp') else 'file'
                collection = 'a{}{}.{}'.format(filetype, stream, version)
            elif re.match(r'atmos_.*_([pm][a-z0-9]).*', line):
                # Atmos netCDF files
                collection = 'an{}.nc.file'.format(re.match(r'atmos_.*_[pm]([a-z0-9]).*',
                                                            line).group(1))
            else:
                # NEMOCICE
                collection = re.match(r'([a-z]*_)?[a-zA-Z0-9]*([io])[_.].*', fname).group(2)
                if 'restart' in fname:
                    collection += 'da.file'
                elif 'trajectory' in fname:
                    collection += 'ni.nc.file'
                else:
                    mean = re.match(r'.*_\d+([dmsyx])_.*', fname).group(1)
                    collection += 'n{}.nc.file'.format(mean)

            try:
                dataset[collection].append(fname)
            except KeyError:
                dataset[collection] = [fname]

    permission = 'a' if os.path.isfile(cylclog) else 'w'
    with open(cylclog, permission) as archive:
        archive.write('[INFO] writing log for ' + os.environ['CYLC_TASK_NAME'])
        archive.write('\n')
        for key in dataset:
            for fn in dataset[key]:
                archive.write('{}/{}/{}\n'.format(archive_set, key, fn))

except IOError:
    print '[ERROR] Logfile did not exist:', logfile
    exit(1)
