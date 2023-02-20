#!/usr/bin/env python
'''
Check that the coupled test for the drivers is MOCI rose stem has terminated
successfully. We dont check in any great details, as the models themselves are
tested and validated in other places
'''

import os
import sys

coupled_directory = os.environ['COUPLED_MODEL_WORK_DIR']
work_dir = os.environ['CYLC_SUITE_WORK_DIR']
datam = os.environ['DATAM']
runid = os.environ['RUNID']
nemohist = os.environ['NEMO_RST']
cicehist = os.environ['CICE_RST']

failure_list = []
coupled_directory = os.path.join(work_dir, '1', coupled_directory)

'''
Part One - check that we have produced a dump
'''
atmos_dump = '{}a.da19780902_00'.format(runid)
if not os.path.isfile(os.path.join(datam, atmos_dump)):
    failure_message = 'Restart file {} expected and not found\n'.format(
        atmos_dump)
    failure_list.append(failure_message)

'''
Part Two - check we have produced (at least one) NEMO dump
'''
nemo_dumps = ['{}o_19780902_restart_0000.nc'.format(runid),
              '{}o_icebergs_19780902_restart_0000.nc'.format(runid)]
for nemo_dump in nemo_dumps:
    if not os.path.isfile(os.path.join(nemohist, nemo_dump)):
        failure_message = 'Restart file {} expected and not found\n'.format(
            nemo_dump)
        failure_list.append(failure_message)

'''
Part Three - check we have produced a CICE dump
'''
cice_dumps = ['{}i.restart.1978-09-02-00000.nc'.format(runid),
              'ice.restart_file']
for cice_dump in cice_dumps:
    if not os.path.isfile(os.path.join(cicehist, cice_dump)):
        failure_message = 'Restart file {} expected and not found\n'.format(
            cice_dump)
        failure_list.append(failure_message)

'''
Part Four - check cpmip.out file
'''
cpmip_fn = 'cpmip.output'
cpmip_fn = os.path.join(coupled_directory, cpmip_fn)
if os.path.isfile(os.path.join(cpmip_fn)):
    # check the cpmip output file contains what we think it should, against
    # a list of line starts
    line_starts = ['Cores per node',
                   'Time in MPI Launcher',
                   'Time in UM model', 'Time in UM coupling',
                   'Time in UM put',
                   'Time in NEMO model', 'Time in NEMO coupling',
                   'Time in NEMO put',
                   'This equates to', 'This run uses', 'Corehours per',
                   'The CPMIP coupling', 'The UM spends', 'This is a fraction',
                   'NEMO spends', 'This is a fraction', 'XIOS spends',
                   'This cycle produces', 'The data intensity metric',
                   'UM Processors', 'UM Available Processors',
                   'NEMO Processors', 'NEMO Available Processors',
                   'XIOS Processors', 'XIOS Available Processors',
                   'Energy cost for run']
    line_number = 1
    with open(cpmip_fn) as cpmip_fh:
        for line, line_start in zip(cpmip_fh.readlines(), iter(line_starts)):
            if not line.lstrip().startswith(line_start):
                failure_message = 'Line {} of {} is expected to start with' \
                                  ' {}\n'.format(
                    line_number, cpmip_fn, line_start)
                failure_list.append(failure_message)
            line_number += 1
else:
    failure_message = 'CPMIP file {} expected and not found\n'.format(cpmip_fn)
    failure_list.append(failure_message)

if failure_list:
    for line in failure_list:
        sys.stderr.write('[FAIL] {}'.format(line))
    sys.exit(1)
