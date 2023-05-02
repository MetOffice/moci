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

# This indicates which flags are assumed to turn on which fields,
# along with an argument, such as 'none' which rules them out from
# being included. The arguments are defined for the sn_rcv_* and
# sn_snd_* variables in NEMO's [namelist:namsbc_cpl] and can be any
# string, but typical values are 'none' or 'oce only'. 

ATM2OCN_FLAGS = {'sn_rcv_antm':{'atmAntmass':'none'},
                 'sn_rcv_atm_dust':{'atmATMDUST':'none'},
                 'sn_rcv_atm_pco2':{'atmATMPCO2':'none'},
                 'sn_rcv_grnm':{'atmGrnmass':'none'},
                 'sn_rcv_iceflx':{'atmTopMlt':'none',
                                  'atmBotMlt':'none'},
                 'sn_rcv_mslp':{'atm_MSLP':'none'},
                 'sn_rcv_qns':{'atm_QnsOce':'none'},
                 'sn_rcv_qsr':{'atm_QsrOce':'none'},
                 'sn_rcv_qtr':{'atmQtr':'none'},
                 'sn_rcv_rnf':{'atm_Runoff':'none'},
                 'sn_rcv_tau':{'atm_OTaux1':'none',
                               'atm_OTauy1':'none'},
                 'sn_rcv_ts_ice':{'atmTsfIce':'none'},
                 'sn_rcv_w10m':{'atm_Wind10':'none'}}

ATM2OCN_FLAGS_NEMO306 = {'sn_rcv_emp':{'atmTotRain':'none',
                                       'atmTotSnow':'none',
                                       'atmTotEvap':'none',
                                       'atmIceEvp':'none'}}

ATM2OCN_FLAGS_NEMO4 = {'sn_rcv_emp':{'atmTotRain':'none',
                                     'atmTotSnow':'none',
                                     'atmTotEvap':'none',
                                     'atmIceEvap':'none'}}

OCN2ATM_FLAGS = {'sn_snd_bio_chloro':{'model01_OBioChlo':'none'},
                 'sn_snd_bio_co2':{'model01_OBioCO2':'none'},
                 'sn_snd_bio_dms':{'model01_OBioDMS':'none'},
                 'sn_snd_cond':{'model01_OIceKn':'none'},
                 'sn_snd_crt':{'model01_O_OCurx1':'none',
                               'model01_O_OCury1':'none'},
                 'sn_snd_mpnd':{'model01_OPndFrc':'none',
                                'model01_OPndTck':'none'},
                 'sn_snd_temp':{'model01_O_SSTSST':'none',
                                'model01_OTepIce':'oce only'},
                 'sn_snd_thick':{'model01_OIceFrc':'none',
                                 'model01_OIceTck':'none',
                                 'model01_OSnwTck':'none'},
                 'sn_snd_thick1':{'model01_OIceFrd':'none'},
                 'sn_snd_ttilyr':{'model01_O_TtiLyr':'none'}}

NAME_FOR_1DFIELD = {'sn_rcv_rnf':{'atmRunff1D':'none'}}

# Each coupling entry can have 6 options
#  - The number of categories
#  - The grid
#  - The type of mapping, e.g. 0D scaler (0D), 1D scaler (1D), bi-cubic (Bc),
#    bi-linear (Bi), conservative destarea (CD), conservative fracarea (CF)
#    and no-mask bi-linear (NB).
#  - The order of mapping (if this is not wanted it is set to -99)
#  - The first field ID
#  - A weighting compared to the other fields in list
ATM2OCN_COUPLINGS = {'atmATMDUST':[1, 't', 'CD', 1, 93, 175],
                     'atmATMPCO2':[1, 't', 'CD', 1, 92, 170],
                     'atmBotMlt':[5, 't', 'CD', 1, 13, 120],
                     'atm_QnsOce':[1, 't', 'CD', 2, 1, 35],
                     'atm_QsrOce':[1, 't', 'CD', 1, 54, 30],
                     'atm_OTaux1':[1, 'u', 'Bi', -99, 23, 0],
                     'atm_OTauy1':[1, 'v', 'Bi', -99, 24, 5],
                     'atmTopMlt':[5, 't', 'CD', 1, 8, 100],
                     'atmTotEvap':[1, 't', 'CD', 2, 7, 50],
                     'atmTotRain':[1, 't', 'CD', 1, 5, 40],
                     'atmTotSnow':[1, 't', 'CD', 1, 6, 45],
                     'atmTsfIce':[5, 't', 'CD', 1, 66, 110],
                     'atm_Wind10':[1, 't', 'CD', 1, 4, 75]}

ATM2OCN_COUPLINGS_NEMO306 = {'atmAntmass':[1, 't', 'NB', 1, 73, 145],
                             'atmGrnmass':[1, 't', 'NB', 1, 72, 140],
                             'atmIceEvp':[5, 't', 'CD', 1, 18, 55],
                             'atm_Runoff':[1, 't', 'CD', 1, 3, 80]}

ATM2OCN_COUPLINGS_NEMO4 = {'atmAntmass':[1, 't', '0D', 1, 73, 145],
                           'atmGrnmass':[1, 't', '0D', 1, 72, 140],
                           'atmIceEvap':[5, 't', 'CD', 1, 18, 55],
                           'atm_MSLP':[1, 't', 'CD', 1, 55, 130],
                           'atmQtr':[5, 't', 'CD', 1, 131, 155],
                           'atmRunff1D':[1, 'r', '1D', 1, 74, 150]}

OCN2ATM_COUPLINGS = {'model01_OBioChlo':[1, 't', 'CF', 1, 94, 130],
                     'model01_OBioCO2':[1, 't', 'CF', 1, 91, 125],
                     'model01_OBioDMS':[1, 't', 'CF', 1, 90, 120],
                     'model01_O_OCurx1':[1, 'u', 'Bi', -99, 51, 70],
                     'model01_O_OCury1':[1, 'v', 'Bi', -99, 52, 75],
                     'model01_OIceFrc':[5, 't', 'CF', 1, 26, 30],
                     'model01_OIceFrd':[5, 't', 'CF', 1, 81, 35],
                     'model01_OIceKn':[5, 't', 'CF', 1, 46, 100],
                     'model01_OIceTck':[5, 't', 'CF', 1, 36, 40],
                     'model01_OPndFrc':[5, 't', 'CF', 1, 56, 80],
                     'model01_OPndTck':[5, 't', 'CF', 1, 61, 85],
                     'model01_OSnwTck':[5, 't', 'CF', 1, 31, 60],
                     'model01_O_SSTSST':[1, 't', 'CF', 1, 25, 0],
                     'model01_OTepIce':[5, 't', 'CF', 1, 41, 10],
                     'model01_O_TtiLyr':[5, 't', 'CF', 1, 41, 5]}

def _determine_default_couplings(origin, ocean_nml, run_info):
    '''
    Determine what the default couplings are
    '''
    default_cpl = []
    n_cpl_freq = 0
    if origin == "ATM":
        if run_info['NEMO_VERSION'] == '306':
            exchange_flags = {**ATM2OCN_FLAGS, **ATM2OCN_FLAGS_NEMO306}
            exchange_couplings = {**ATM2OCN_COUPLINGS,
                                  **ATM2OCN_COUPLINGS_NEMO306}
        else:
            exchange_flags = {**ATM2OCN_FLAGS, **ATM2OCN_FLAGS_NEMO4}
            exchange_couplings = {**ATM2OCN_COUPLINGS,
                                  **ATM2OCN_COUPLINGS_NEMO4}
        destinations = ["OCN"]
        weight_ref = 300
    elif origin == "OCN":
        exchange_flags = OCN2ATM_FLAGS
        exchange_couplings = OCN2ATM_COUPLINGS
        if 'junior' in run_info['exec_list']:
            destinations = ["ATM", "JNR"]
        else:
            destinations = ["ATM"]
        weight_ref = 100
    else:
        # There is currently no default coupling from JNR or any
        # component which isn't ATM or OCN
        exchange_flags = []

    # Need to determine the coupling list
    for flag in exchange_flags:
        # Check NEMO namelist to see if this field should be
        # coupled
        if flag in ocean_nml['namsbc_cpl']:
            # Setting 'coupled1d' can change the name and definitions
            # of the coupling field
            if ocean_nml['namsbc_cpl'][flag][0] == 'coupled1d':
                coupling_fields = NAME_FOR_1DFIELD[flag]
            else:
                coupling_fields = exchange_flags[flag]
            # Loop across the fields associated with this flag
            for cpl_field in coupling_fields:
                # See if field should not be used
                if ocean_nml['namsbc_cpl'][flag][0] != \
                   coupling_fields[cpl_field]:
                    # Loop over the categories for this field
                    vind = exchange_couplings[cpl_field][4]
                    for i in range(1, exchange_couplings[cpl_field][0]+1):

                        # Determine the weighting for this field
                        weighting = weight_ref + \
                                    exchange_couplings[cpl_field][5] + i - 1
                        # Determine the outgoing name
                        if exchange_couplings[cpl_field][0] > 1:
                            name_out = '{0}_cat{1:02d}'.format(cpl_field, i)
                        else:
                            name_out = cpl_field

                        # Loop across the destinations
                        for dest in destinations:
                            grid = exchange_couplings[cpl_field][1]
                            # Determine the type of mapping
                            if ocean_nml['namsbc_cpl'][flag][0] == 'coupled0d':
                                # This is passing a OD scalar field
                                mapping = 'OneVal'
                            else:
                                mapping = write_namcouple.RMP_MAPPING[
                                    exchange_couplings[cpl_field][2]]

                            # Add field to list
                            default_cpl.append(
                                write_namcouple.NamcoupleEntry(
                                    name_out, vind, grid,
                                    origin, dest, 1, False, mapping,
                                    exchange_couplings[cpl_field][3],
                                    weighting, False, n_cpl_freq, None))

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
