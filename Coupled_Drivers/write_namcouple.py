#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.
 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    write_namcouple.py

DESCRIPTION
    Write namcouple file at run time.
'''
import sys
import itertools
import common
import default_couplings
import error
import write_cf_name_table
import write_namcouple_fields
import write_namcouple_header

# Dictionary containing the RMP mappings
RMP_MAPPING = {'Bc':'BICUBIC',
               'Bi':'BILINEA',
               'CD':'CONSERV_DESTAREA',
               'CF':'CONSERV_FRACAREA',
               '0D':'OneVal',
               '1D':'OneD',
               'NB':'nomask_BILINEA',
               'remove':'remove'}

class NamcoupleEntry():
    '''
    Container to hold the information for one namcouple entry
    '''

    def __init__(self, name_out, field_id, grid, origin, dest, nlev, l_soil,
                 mapping, mapping_type, weight, l_hybrid, n_cpl_freq,
                 override_cpl_freq):
        self.name_out = name_out
        self.field_id = field_id
        self.grid = grid
        self.origin = origin
        self.dest = dest
        self.nlev = nlev
        self.l_soil = l_soil
        self.mapping = mapping
        self.mapping_type = mapping_type
        self.weight = weight
        self.l_hybrid = l_hybrid
        self.n_cpl_freq = n_cpl_freq
        self.override_cpl_freq = override_cpl_freq

    def __repr__(self):
        return repr((self.name_out, self.field_id, self.grid, self.origin,
                     self.dest, self.nlev, self.l_soil, self.mapping,
                     self.mapping_type, self.weight, self.l_hybrid,
                     self.n_cpl_freq, self.override_cpl_freq))

def _print_run_info(run_info):
    '''
    Print the information in run_info
    '''
    sys.stdout.write('[INFO] Display the contents of run_info:\n')
    sys.stdout.write('[INFO] -------- Resolutions -------- \n')
    if 'ATM_grid' in run_info:
        sys.stdout.write('[INFO] Atmosphere:        %s (%d, %d)\n' %
                         (run_info['ATM_grid'], run_info['ATM_resol'][0],
                          run_info['ATM_resol'][1]))
    if 'JNR_grid' in run_info:
        sys.stdout.write('[INFO] Junior atmosphere: %s (%d, %d)\n' %
                         (run_info['JNR_grid'], run_info['JNR_resol'][0],
                          run_info['JNR_resol'][1]))
    if 'OCN_grid' in run_info:
        # If running ATM<->JNR coupling we can have an ocean resolution
        # without an ocean.
        if 'OCN_resol' in run_info:
            sys.stdout.write('[INFO] Ocean:             %s (%d, %d)' %
                             (run_info['OCN_grid'], run_info['OCN_resol'][0],
                              run_info['OCN_resol'][1]))
        else:
            sys.stdout.write('[INFO] Ocean:             %s' %
                             run_info['OCN_grid'])
        if 'NEMO_VERSION' in run_info:
            sys.stdout.write('   (NEMO version: %s)\n' %
                             run_info['NEMO_VERSION'])
        else:
            sys.stdout.write('\n')
    if 'riv3' in run_info:
        if run_info['riv3'] > 0:
            sys.stdout.write('[INFO] Number of rivers:  %d\n' %
                             run_info['riv3'])

    sys.stdout.write('[INFO] -------- Coupling frequencies (in mins) '
                     '-------- \n')
    comp_order = ['ATM', 'JNR', 'OCN']
    comp_list = [comp for comp in comp_order if '{}_resol'.format(comp) in
                 run_info]
    for component1, component2 in itertools.permutations(comp_list, r=2):
        key = component2 + '2' + component1 + '_freq'
        sys.stdout.write('[INFO] %s -> %s:           %0.1f\n' %
                         (component2, component1,
                          (run_info[key][0]/60.0)))
        key2 = 'l_hyb_stats_' + component2 + '2' + component1
        if key2 in run_info:
            if run_info[key2]:
                sys.stdout.write('[INFO] %s -> %s for stats: %0.1f\n' %
                                 (component2, component1,
                                  (run_info[key][1]/60.0)))
        key = component1 + '2' + component2 + '_freq'
        sys.stdout.write('[INFO] %s -> %s:           %0.1f\n' %
                         (component1, component2,
                          (run_info[key][0]/60.0)))
        key2 = 'l_hyb_stats_' + component1 + '2' + component2
        if key2 in run_info:
            if run_info[key2]:
                sys.stdout.write('[INFO] %s -> %s for stats: %0.1f\n' %
                                 (component2, component1,
                                  (run_info[key][1]/60.0)))
    if 'ATM_grid' in run_info:
        sys.stdout.write('[INFO] -------- Atmosphere information -------- \n')
        sys.stdout.write('[INFO] Atmosphere levels:              %d\n' %
                         run_info['ATM_model_levels'])
        sys.stdout.write('[INFO] Soil levels:                    %d\n' %
                         run_info['ATM_soil_levels'])
        sys.stdout.write('[INFO] Number of vegetation tiles:     %d\n' %
                         run_info['ATM_veg_tiles'])
        sys.stdout.write('[INFO] Number of non-vegetation tiles: %d\n' %
                         run_info['ATM_non_veg_tiles'])
        sys.stdout.write('[INFO] STASHmaster directory:          %s\n' %
                         run_info['STASHMASTER'])
    sys.stdout.write('[INFO] -------- Namcouple settings -------- \n')
    sys.stdout.write('[INFO] nlogprt: %d' % run_info['nlogprt'][0])
    if len(run_info['nlogprt']) == 2:
        sys.stdout.write(' %d\n' % run_info['nlogprt'][1])
    else:
        sys.stdout.write('\n')
    sys.stdout.write('[INFO] Executable list:\n')
    for execut in run_info['exec_list']:
        sys.stdout.write('[INFO]    - %s\n' % execut)
    if 'expout' in run_info:
        sys.stdout.write('[INFO] Fields with EXPOUT argument:\n')
        for field in run_info['expout']:
            sys.stdout.write('[INFO]    - %s\n' % field)
    if 'rmp_create' in run_info:
        sys.stdout.write('[INFO] Fields where remapping files will be '
                         'created are:\n')
        for field in run_info['rmp_create']:
            sys.stdout.write('[INFO]    - %s\n' % field)
    sys.stdout.write('[INFO] -------- Files -------- \n')
    sys.stdout.write('[INFO] File containing coupling frequencies: %s\n' %
                     run_info['SHARED_FILE'])
    if 'nemo_nl' in run_info:
        sys.stdout.write('[INFO] Default couplings determined from:    %s\n' %
                         run_info['nemo_nl'])

def _checks_on_run_info(run_info):
    '''
    Run some checks on the data in run_info
    '''
    # If coupling contains both hybrid components, check the model_levels
    # are the same for both.
    if 'ATM_model_levels' in run_info and 'JNR_model_levels' in run_info:
        if run_info['ATM_model_levels'] != run_info['JNR_model_levels']:
            sys.stderr.write('[FAIL] model_levels for Snr (=%d) and Jnr '
                             '(=%d) are different.\n' %
                             (run_info['ATM_model_levels'],
                              run_info['JNR_model_levels']))
            sys.exit(error.DIFFERENT_MODEL_LEVELS)
    if 'ATM_soil_levels' in run_info and 'JNR_soil_levels' in run_info:
        if run_info['ATM_soil_levels'] != run_info['JNR_soil_levels']:
            sys.stderr.write('[FAIL] soil levels for Snr (=%d) and Jnr '
                             '(=%d) are different.\n' %
                             (run_info['ATM_soil_levels'],
                              run_info['JNR_soil_levels']))
            sys.exit(error.DIFFERENT_SOIL_LEVELS)

    # If stats are turned on, we want to sample the core fields for
    # stats at least as often as the stat fields.
    if 'l_hyb_stats_ATM2JNR' in run_info:
        if run_info['ATM2JNR_freq'][0] > run_info['ATM2JNR_freq'][1]:
            sys.stdout.write('[INFO] matching the main coupling frequency '
                             'between ATM->JNR to the stats frequency\n')
            run_info['ATM2JNR_freq'][0] = run_info['ATM2JNR_freq'][1]
    if 'l_hyb_stats_JNR2ATM' in run_info:
        if run_info['JNR2ATM_freq'][0] > run_info['JNR2ATM_freq'][1]:
            sys.stdout.write('[INFO] matching the main coupling frequency '
                             'between JNR->ATM to the stats frequency\n')
            run_info['JNR2ATM_freq'][0] = run_info['JNR2ATM_freq'][1]

    return run_info

def add_to_cpl_list(origin, l_hybrid, n_cpl_freq, send_list_raw):
    '''
    Add a new set of couplings to model_snd_list
    '''
    mapping = None
    weighting = None
    model_snd_list = []
    if not isinstance(send_list_raw, list):
        send_list_raw = [send_list_raw]

    # Loop across the raw entries
    for cpl_entry_raw in send_list_raw:
        if cpl_entry_raw == 'default':
            # Entry will later be filled with the default options
            model_snd_list.append(
                NamcoupleEntry('default', '?', '?', origin, '?', '?', '?',
                               '?', '?', '?', l_hybrid, n_cpl_freq, None))
        else:
            # A raw coupling entry can have up to 7 arguments:
            # <source name>;<vind>;<grid>;<destination>;<number of level>;
            # <mapping&mapping order>;<weighting>, e.g.
            # model01_O_SSTSST;25;t;ATM;1;CF;100. See the subsection on
            # `Explicitly specifying each coupling' in UMDP C02 for more
            # information on this.

            # Default options
            nlev = 1
            mapping_type = -99

            if isinstance(cpl_entry_raw, str) and ';' in cpl_entry_raw:
                # Split the input
                parts = cpl_entry_raw.split(';')
                # Check we have enough compulsory input
                if len(parts) < 6:
                    sys.stderr.write('[FAIL] Insufficent information in %s\n' %
                                     cpl_entry_raw)
                    sys.exit(error.MISSING_NAMCOUPLE_INPUT)
                # Set the fields we should know
                name_out = parts[0]
                field_id = int(parts[1])
                grid = parts[2]
                dests = parts[3].split('&')
                # Check if number of level are provided
                if len(parts) > 4:
                    nlev = int(parts[4])
                # Check if a mapping is provided
                if len(parts) > 5:
                    sub_parts = parts[5].split('&')
                    if sub_parts[0] in RMP_MAPPING:
                        mapping = RMP_MAPPING[sub_parts[0]]
                    else:
                        sys.stderr.write("[FAIL] Don't recognise this "
                                         "mapping: %s.\n" % parts[5])
                        sys.exit(error.UNRECOGNISED_MAPPING)
                    if len(sub_parts) > 1:
                        mapping_type = int(sub_parts[1])
                else:
                    if not mapping:
                        sys.stderr.write('[FAIL] Need to specify a mapping '
                                         'for first entry %s\n' %
                                         cpl_entry_raw)
                        sys.exit(error.MISSING_MAPPING)
                # Check if we have a coupling weighting
                if len(parts) > 6:
                    weighting = int(parts[6])
                else:
                    if not weighting:
                        sys.stderr.write('[FAIL] Need to specify a weighting '
                                         'for first entry.\n')
                        sys.exit(error.MISSING_WEIGHTING)

                # Loop over the destinations
                for dest in dests:
                    model_snd_list.append(
                        NamcoupleEntry(name_out, field_id, grid, origin,
                                       dest, nlev, '?', mapping, mapping_type,
                                       weighting, l_hybrid, n_cpl_freq, None))
                    # Just add to the default weighting
                    weighting += 2
            else:
                sys.stderr.write('[FAIL] the following coupling entry looks '
                                 'to be in the wrong format: %s\n' %
                                 cpl_entry_raw)
                sys.exit(error.WRONG_CPL_FORMAT)

    return model_snd_list

def write_namcouple(common_env, run_info, coupling_list):
    '''
    Write the namcouple file
    '''
    # Key information is contained in run_info
    _print_run_info(run_info)

    # Run some checks on the data in run_info
    run_info = _checks_on_run_info(run_info)

    # See if any default couplings need adding
    for nam_entry in coupling_list:
        if 'default' in nam_entry.name_out:
            coupling_list = \
                default_couplings.add_default_couplings(run_info,
                                                        coupling_list)
            break

    # See if any couplings need removing
    store_coupling_list = []
    for nam_entry in coupling_list:
        if nam_entry.mapping != 'remove':
            store_coupling_list.append(nam_entry)
    coupling_list = store_coupling_list

    # Open the file
    nam_file = common.open_text_file('namcouple', 'w')

    # Create the header
    write_namcouple_header.write_namcouple_header(common_env, nam_file,
                                                  run_info, len(coupling_list))

    # Sort the coupling_list by weighting
    coupling_list = sorted(coupling_list,
                           key=lambda nam_entry: nam_entry.weight)

    # Write the coupling fields
    cf_names = write_namcouple_fields.write_namcouple_fields(
        nam_file, run_info, coupling_list)

    # Close file
    nam_file.write('#\n$END\n')
    nam_file.close()

    # Write cf_name_table.txt file
    write_cf_name_table.write_cf_name_table(cf_names)

    # Now that namcouple has been created, we can create the transient
    # field namelist
    _, _ = common.exec_subproc('./OASIS_fields')
