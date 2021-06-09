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
    default_couplings.py

DESCRIPTION
    Add in the default couplings.
    This is only used when creating the namcouple at run time.
'''
import sys
import error
import write_namcouple
try:
    import f90nml
except ImportError:
    pass

# This indicates which flags are assumed to turn on which
# fields
ATM2OCN_FLAGS = {'sn_rcv_tau':['atm_OTaux1', 'atm_OTauy1'],
                 'sn_rcv_qsr':['atm_QsrOce'],
                 'sn_rcv_qns':['atm_QnsOce'],
                 'sn_rcv_emp':['atmTotRain', 'atmTotSnow',
                               'atmTotEvap', 'atmIceEvp'],
                 'sn_rcv_w10m':['atm_Wind10'],
                 'sn_rcv_rnf':['atm_Runoff'],
                 'sn_rcv_iceflx':['atmTopMlt', 'atmBotMlt'],
                 'sn_rcv_ts_ice':['atmTsfIce'],
                 'sn_rcv_grnm':['atmGrnmass'],
                 'sn_rcv_antm':['atmAntmass'],
                 'sn_rcv_atm_pco2':['atmATMPCO2'],
                 'sn_rcv_atm_dust':['atmATMDUST']}

ATM2OCN_FLAG_ORDER = ['sn_rcv_tau', 'sn_rcv_qsr', 'sn_rcv_qns',
                      'sn_rcv_emp', 'sn_rcv_w10m', 'sn_rcv_rnf',
                      'sn_rcv_iceflx', 'sn_rcv_ts_ice', 'sn_rcv_grnm',
                      'sn_rcv_antm', 'sn_rcv_atm_pco2', 'sn_rcv_atm_dust']

OCN2ATM_FLAGS = {'sn_snd_temp':['model01_O_SSTSST', 'model01_OTepIce'],
                 'sn_snd_thick':['model01_OIceFrc', 'model01_OIceTck',
                                 'model01_OSnwTck'],
                 'sn_snd_thick1':['model01_OIceFrd'],
                 'sn_snd_crt':['model01_O_OCurx1', 'model01_O_OCury1'],
                 'sn_snd_mpnd':['model01_OPndFrc', 'model01_OPndTck'],
                 'sn_snd_cond':['model01_OIceKn'],
                 'sn_snd_bio_dms':['model01_OBioDMS'],
                 'sn_snd_bio_co2':['model01_OBioCO2'],
                 'sn_snd_bio_chloro':['model01_OBioChlo']}

OCN2ATM_FLAG_ORDER = ['sn_snd_temp', 'sn_snd_thick', 'sn_snd_thick1',
                      'sn_snd_crt', 'sn_snd_mpnd', 'sn_snd_cond',
                      'sn_snd_bio_dms', 'sn_snd_bio_co2', 'sn_snd_bio_chloro']

NAME_FOR_1DFIELD = {'sn_rcv_rnf':['atmRunff1D']}

# Each coupling entry can have 5 options
#  - The number of categories
#  - The grid
#  - The type of mapping
#  - The order of mapping (if this is not wanted it is set to -99)
#  - The first field ID
# Note that a coupling entry would typically have a 'weighting' for the
# coupling, but this is not specified in ATM2OCN_COUPLINGS or
# OCN2ATM_COUPLINGS. Instead the 'weighting' is set in
# _determine_default_couplings.
ATM2OCN_COUPLINGS = {'atmAntmass':[1, 't', 'NB', 1, 73],
                     'atmATMDUST':[1, 't', 'CD', 1, 93],
                     'atmATMPCO2':[1, 't', 'CD', 1, 92],
                     'atmBotMlt':[5, 't', 'CD', 1, 13],
                     'atmGrnmass':[1, 't', 'NB', 1, 72],
                     'atmIceEvp':[5, 't', 'CD', 2, 18],
                     'atm_QsrOce':[1, 't', 'CD', 1, 54],
                     'atm_QnsOce':[1, 't', 'CD', 2, 1],
                     'atm_Runoff':[1, 't', 'CD', 1, 3],
                     'atmRunff1D':[1, 'r', '1D', 1, 74],
                     'atm_OTaux1':[1, 'u', 'Bi', -99, 23],
                     'atm_OTauy1':[1, 'v', 'Bi', -99, 24],
                     'atmTopMlt':[5, 't', 'CD', 1, 8],
                     'atmTotRain':[1, 't', 'CD', 1, 5],
                     'atmTotSnow':[1, 't', 'CD', 1, 6],
                     'atmTotEvap':[1, 't', 'CD', 2, 7],
                     'atmTsfIce':[5, 't', 'CD', -99, 66],
                     'atm_Wind10':[1, 't', 'CD', 1, 4]}

OCN2ATM_COUPLINGS = {'model01_O_OCurx1':[1, 'u', 'Bi', -99, 51],
                     'model01_O_OCury1':[1, 'v', 'Bi', -99, 52],
                     'model01_O_SSTSST':[1, 't', 'CF', -99, 25],
                     'model01_OBioChlo':[1, 't', 'CF', -99, 94],
                     'model01_OBioCO2':[1, 't', 'CF', -99, 91],
                     'model01_OBioDMS':[1, 't', 'CF', -99, 90],
                     'model01_OIceFrc':[5, 't', 'CF', -99, 26],
                     'model01_OIceFrd':[5, 't', 'CF', -99, 81],
                     'model01_OIceKn':[5, 't', 'CF', -99, 46],
                     'model01_OIceTck':[5, 't', 'CF', -99, 36],
                     'model01_OPndFrc':[5, 't', 'CF', -99, 56],
                     'model01_OPndTck':[5, 't', 'CF', -99, 61],
                     'model01_OSnwTck':[5, 't', 'CF', -99, 31],
                     'model01_OTepIce':[5, 't', 'CF', -99, 41]}


def _determine_default_couplings(origin, ocean_nml, run_info):
    '''
    Determine what the default couplings are
    '''
    default_cpl = []
    n_cpl_freq = 0
    if origin == "ATM":
        exchange_flag_order = ATM2OCN_FLAG_ORDER
        exchange_flags = ATM2OCN_FLAGS
        exchange_couplings = ATM2OCN_COUPLINGS
        destinations = ["OCN"]
        weighting = 300
    elif origin == "OCN":
        exchange_flag_order = OCN2ATM_FLAG_ORDER
        exchange_flags = OCN2ATM_FLAGS
        exchange_couplings = OCN2ATM_COUPLINGS
        if 'junior' in run_info['exec_list']:
            destinations = ["ATM", "JNR"]
        else:
            destinations = ["ATM"]
        weighting = 100
    else:
        # There is currently no default coupling from JNR or any
        # component which isn't ATM or OCN
        exchange_flag_order = []

    # Need to determine the coupling list
    for flag in exchange_flag_order:
        # Check NEMO namelist to see if this field should be
        # coupled
        if flag in ocean_nml['namsbc_cpl']:
            # Setting 'coupled1d' can change the name and definitions
            # of the coupling field
            if ocean_nml['namsbc_cpl'][flag][0] == 'coupled1d':
                coupling_fields = NAME_FOR_1DFIELD[flag]
            else:
                coupling_fields = exchange_flags[flag]
            if ocean_nml['namsbc_cpl'][flag][0] != 'none':
                # Loop across the fields which this flag activates
                for cpl_field in coupling_fields:
                    # Loop over the categories for this field
                    vind = exchange_couplings[cpl_field][4]
                    for i in range(1, exchange_couplings[cpl_field][0]+1):
                        if exchange_couplings[cpl_field][0] > 1:
                            name_out = ('%s_cat%02d' % (cpl_field, i))
                        else:
                            name_out = cpl_field
                        # Loop across the destinations
                        for dest in destinations:
                            # Determine the type of mapping
                            if ocean_nml['namsbc_cpl'][flag][0] == 'coupled0d':
                                # This is passing a scalar field
                                grid = 's'
                                mapping = 'Scalar'
                            else:
                                grid = exchange_couplings[cpl_field][1]
                                mapping = write_namcouple.RMP_MAPPING[
                                    exchange_couplings[cpl_field][2]]
                            # Add field to list
                            default_cpl.append(
                                write_namcouple.NamcoupleEntry(
                                    name_out, vind, grid,
                                    origin, dest, 1, False, mapping,
                                    exchange_couplings[cpl_field][3],
                                    weighting, False, n_cpl_freq))
                            weighting += 2
                        # Move to next field
                        vind += 1

    return default_cpl


def add_default_couplings(run_info, coupling_list):
    '''
    Replaces coupling entries of 'default' with the couplings
    which are usual
    '''
    # Find where the default entries are
    i_default = []
    i = 0
    for nam_entry in coupling_list:
        if 'default' in nam_entry.name_out:
            i_default.append(i)
        i += 1

    # Read in the ocean namelist
    if 'nemo_nl' in run_info:
        ocean_nml = f90nml.read(run_info['nemo_nl'])
        if 'namsbc_cpl' not in ocean_nml:
            sys.stderr.write('[FAIL] missing namelist namsbc_cpl.\n')
            sys.exit(error.MISSING_NAMSBC_CPL)

        # Loop through the default entries
        for i_entry in i_default:
            nam_entry = coupling_list[i_entry]
            # Return a list of the fields normally coupled from this
            # source
            default_cpl = _determine_default_couplings(nam_entry.origin,
                                                       ocean_nml, run_info)

            # Loop through these new fields and add any which are not
            # already in coupling_list
            for default_entry in default_cpl:
                # Check if entry is already in list
                l_add = True
                for nam_entry in coupling_list:
                    if default_entry.name_out == nam_entry.name_out and \
                            default_entry.dest == nam_entry.dest:
                        l_add = False
                        break
                # Add entry to list
                if l_add:
                    coupling_list.append(default_entry)

    # Remove the default entry
    for i_entry in reversed(i_default):
        del coupling_list[i_entry]

    return coupling_list
