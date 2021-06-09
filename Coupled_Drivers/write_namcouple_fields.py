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
    write_namcouple_fields.py

DESCRIPTION
    Write the main coupling field entries in the namcouple at run time.
'''
import os
import sys
import error
from mule.stashmaster import STASHmaster
import write_cf_name_table

# The part of name used in namcouple to identify the component
NAM_COMP_NAMES = {'ATM':'atm', 'JNR':'jnr', 'OCN':'model01_O'}

# The grid names for a ATMOS<->OCN coupling
ATM2OCN_GRIDS = {'ATM':{'u':'aum3', 'v':'avm3', 't':'atm3',
                        'r':'riv3', 's':'scal'},
                 'JNR':{'u':'jum3', 'v':'jvm3', 't':'jtm3',
                        'r':'riv3', 's':'scal'},
                 'OCN':{'u':'uor1', 'v':'vor1', 't':'tor1',
                        'r':'riv3', 's':'scal'}}

class StashInfo():
    '''
    For a given stash entry, this contains all the information we need here
    '''

    def __init__(self, longname, grid, level_f, level_l, pseudo_l):
        self.longname = longname
        self.grid = grid
        self.level_f = level_f
        self.level_l = level_l
        self.pseudo_l = pseudo_l

    def __repr__(self):
        return repr((self.longname, self.grid, self.level_f, self.level_l,
                     self.pseudo_l))

def _determine_grid(grid_num, stash_code):
    '''
    Determine the grid type
    '''
    if grid_num < 6:
        grid = 't'
    elif grid_num == 18:
        grid = 'u'
    elif grid_num == 19:
        grid = 'v'
    elif grid_num == 21:
        # It's necessary to be have at least one vegetation/soil (s) field
        # and at least one ice (i) field, so the land field - which is a
        # combination of these two remappings - can be generated.
        if stash_code == 704:
            # On vegetation/soil grid
            grid = 's'
        elif stash_code == 705:
            # Ice grid
            grid = 'i'
        else:
            # On land grid
            grid = 'l'
    else:
        sys.stderr.write('[FAIL] unrecognised grid=%d.\n' % grid_num)
        grid = None

    return grid

def _determine_levels(model_levels, soil_levels, n_veg_tiles,
                      n_non_veg_tiles, grid_num, level_f, level_l, pseudo_l):
    '''
    Determine the number of vertical levels
    '''
    # Determine if this field is in the soil/land
    if grid_num == 21:
        # This field is in the soil/land.
        l_soil = True
        # Check if one level
        if level_f == -1 and level_l == -1:

            # Check if no pseudo levels
            if pseudo_l == 0:
                return 1, l_soil

            # Check if pseudo levels are vegetation + non-vegetation tiles
            if pseudo_l == 7:
                return (n_veg_tiles + n_non_veg_tiles), l_soil

            # Check if pseudo levels are vegetation tiles
            if pseudo_l == 8:
                return n_veg_tiles, l_soil

            # If not returned by now, then something has gone wrong.
            sys.stderr.write('[FAIL] land-only field with pseudo_l=%d '
                             'is not recognised.\n' % pseudo_l)
            return -99, l_soil

        # Check if soil field
        if level_f == 8 and level_l == 9:
            return soil_levels, l_soil

        # If not returned by now, then something has gone wrong.
        sys.stderr.write('[FAIL] land-only field with level_f=%d and '
                         'level_l=%d is not recognised.\n' %
                         (level_f, level_l))
        return -99, l_soil

    # Reaching here, implies that field is in the atmosphere.
    l_soil = False

    # Check if this is a 2d field
    if level_f == -1:
        # Only one level for 2d fields
        return 1, l_soil

    # Determine the first level
    if level_f in (10, 38, 40):
        first_lev = 0
    elif level_f == 1:
        first_lev = 1
    else:
        sys.stderr.write('[FAIL] unrecognised levelF=%d.\n' % level_f)
        first_lev = -99

    # Determine the last level
    if level_l in (2, 3, 11, 14):
        last_lev = model_levels
    elif level_l == 19:
        last_lev = model_levels + 1
    else:
        sys.stderr.write('[FAIL] unrecognised levelL=%d.\n' % level_l)
        last_lev = -99

    # Check for error in either first_lev or last_lev
    if first_lev < 0 or last_lev < 0:
        return -99, l_soil

    # Return the total number of levels
    return (last_lev - first_lev + 1), l_soil

def _coupling_freq(nam_entry, run_info):
    '''
    Determine the coupling frequency
    '''
    # Find the coupling frequency in run_info
    cpl_var = nam_entry.origin + '2' + nam_entry.dest + '_freq'
    if not cpl_var in run_info:
        sys.stderr.write('[FAIL] %s is not found in run_info for %s.\n' %
                         (cpl_var, nam_entry.name_out))
        sys.exit(error.NOT_FOUND_CPL_VAR)
    if len(run_info[cpl_var]) < nam_entry.n_cpl_freq:
        sys.stderr.write('[FAIL] not enough coupling frequencies '
                         'for %s.\n' % cpl_var)
        sys.exit(error.NOT_ENOUGH_CPL_FREQ)
    cpl_freq = run_info[cpl_var][nam_entry.n_cpl_freq]

    return cpl_freq

def _read_stashmaster(stashmaster_dir):
    '''
    Read the stashmaster file and store the information we need
    '''
    # Check that STASHmaster_A file exists
    stashmaster_a = stashmaster_dir + '/STASHmaster_A'
    if not os.path.exists(stashmaster_a):
        sys.stderr.write('[FAIL] failed to find STASHmaster_A at %s.\n' %
                         stashmaster_a)
        sys.exit(error.MISSING_STASHMASTER_A)

    # Read STASHmaster_A
    stashmaster_info = {}
    stash_data = STASHmaster.from_file(stashmaster_a)
    for stash_code in stash_data.keys():
        stash_code = int(stash_code)
        stash_info = stash_data[stash_code]
        stashmaster_info[stash_code] = StashInfo(stash_info.name,
                                                 stash_info.grid,
                                                 int(stash_info.levelF),
                                                 int(stash_info.levelL),
                                                 int(stash_info.psuedL))
    return stashmaster_info

def _snr2jnr_field_info(nam_entry, model_levels, soil_levels, n_veg_tiles,
                        n_non_veg_tiles, stashmaster_info):
    '''
    Field information for Snr<->Jnr hybrid coupling
    '''
    # Determine the name_in
    if nam_entry.dest == 'JNR':
        dest_ident = 'j'
    else:
        dest_ident = 's'
    name_in = nam_entry.name_out[0:5] + dest_ident + \
        nam_entry.name_out[6:9] + 'r'

    # Determine if stash code is in stashmaster_info
    stash_code = int(nam_entry.name_out[0:5])
    if stash_code in stashmaster_info:
        # Determine which grid we're on
        grid = _determine_grid(stashmaster_info[stash_code].grid, stash_code)
        if not grid:
            # There has been error
            sys.stderr.write('[FAIL] failure for stash code %d.\n' %
                             stash_code)
            sys.exit(error.UNRECOGNISED_GRID)
        # Determine the number of vertical levels and if field is
        # found in the atmosphere or the land/soil.
        nlev, l_soil = _determine_levels(model_levels, soil_levels,
                                         n_veg_tiles, n_non_veg_tiles,
                                         stashmaster_info[stash_code].grid,
                                         stashmaster_info[stash_code].level_f,
                                         stashmaster_info[stash_code].level_l,
                                         stashmaster_info[stash_code].pseudo_l)
        if nlev < 0:
            # There has been error
            sys.stderr.write('[FAIL] failure for stash code %d.\n' %
                             stash_code)
            sys.exit(error.UNRECOGNISED_LEVEL)
    else:
        sys.stderr.write('[FAIL] not found stash code %d in '
                         'STASHmaster information.\n' % stash_code)
        sys.exit(error.NOT_FOUND_STASH_CODE)

    return name_in, stashmaster_info[stash_code].longname, grid, nlev, l_soil

def _atm2ocn_field_info(nam_entry, cf_names, cf_table_num, n_cf_table):
    '''
    Field information for ATM<->OCN coupling
    '''
    # Determine the name_in
    name_in_comp = NAM_COMP_NAMES[nam_entry.origin]
    name_out_comp = NAM_COMP_NAMES[nam_entry.dest]
    name_in = nam_entry.name_out.replace(name_in_comp, name_out_comp)

    # Determine the cf_name_table.txt attributes
    cf_code = \
        nam_entry.name_out.replace(name_in_comp, '').split('_cat')[0]
    if cf_code in write_cf_name_table.CF_ATTR:
        longname = write_cf_name_table.CF_ATTR[cf_code][0]
        unit = write_cf_name_table.CF_ATTR[cf_code][1]
    else:
        sys.stdout.write('[WARNING] full name and units unknown for %s.\n'
                         % nam_entry.name_out)
        longname = "unknown_name"
        unit = "unknown_unit"

    # See if we already have this entry in CF table
    if cf_code in cf_table_num:
        cf_table_number = cf_table_num[cf_code]
    else:
        cf_names.append(write_cf_name_table.CfNameTableEntry(longname, unit))
        n_cf_table += 1
        cf_table_num[cf_code] = n_cf_table
        cf_table_number = n_cf_table

    return name_in, cf_names, cf_table_number, cf_table_num, n_cf_table

def _write_transdef(nam_file, nam_entry, cpl_freq, n_field, longname):
    '''
    Write the TRANSDEF information
    '''
    # Choice sensible units to display the coupling frequency
    # (129,600s is 1.5 days, and 5,400s is 1.5 hours)
    if cpl_freq > 129600:
        # Display in units of days
        display_freq = int(cpl_freq / 86400 + 0.5)
        display_unit = 'days'
    elif cpl_freq > 5400:
        # Display in units of hours
        display_freq = int(cpl_freq / 3600 + 0.5)
        display_unit = 'hrs'
    else:
        # Display in units of minutes
        display_freq = int(cpl_freq / 60 + 0.5)
        display_unit = 'mins'

    # Information for coupling
    nam_file.write('#---------------------------------------------------\n')
    nam_file.write('# %s' % longname)
    if nam_entry.l_hybrid:
        nam_file.write(' (stash %s,%s)' % (nam_entry.name_out[0:2],
                                           nam_entry.name_out[2:5]))
    nam_file.write(' (weighting %d)\n' % nam_entry.weight)
    nam_file.write('# %s --> %s every %d%s (%ds)' %
                   (nam_entry.origin, nam_entry.dest, display_freq,
                    display_unit, cpl_freq))
    if nam_entry.nlev == 1:
        nam_file.write(', 1 level\n')
    else:
        nam_file.write(', %d levels\n' % nam_entry.nlev)
    nam_file.write('#---------------------------------------------------\n')

    # For scalar field the grid is not specified
    if nam_entry.mapping == 'Scalar':
        grid = '0'
    elif nam_entry.mapping == 'OneD':
        grid = '1'
    else:
        grid = nam_entry.grid.upper()

    # TRANSDEF line
    nam_file.write('# TRANSDEF: %s%s %s%s %d %d ' %
                   (nam_entry.origin, grid, nam_entry.dest, grid,
                    n_field, nam_entry.field_id))
    if nam_entry.mapping_type > 0:
        nam_file.write('%d ' % nam_entry.mapping_type)
    nam_file.write('###\n')

def _write_main_line(nam_file, nam_entry, cpl_freq, name_in,
                     cf_table_number, n_trans, cpl_restart_file,
                     run_info):
    '''
    Write the main namcouple line which contains the sent and
    received fields and the coupling frequency
    '''
    # See if this should be EXPOUT
    exp_type = 'EXPORTED'
    if 'expout' in run_info:
        if nam_entry.l_hybrid:
            name_match_str = nam_entry.name_out[0:6]
        else:
            name_match_str = nam_entry.name_out
        for expout_entry in run_info['expout']:
            if expout_entry == name_match_str:
                exp_type = 'EXPOUT'

    # Create the name_out string for all levels
    name_out_str = nam_entry.name_out
    name_in_str = name_in
    if nam_entry.nlev > 1:
        for level in range(2, nam_entry.nlev+1):
            name_out_str = name_out_str + ':' + nam_entry.name_out[0:6] + \
                '{:03d}'.format(level) + 's'
            name_in_str = name_in_str  + ':' + name_in[0:6] + \
                '{:03d}'.format(level) + 'r'
    # The fields out and in
    nam_file.write(' %s %s ' % (name_out_str, name_in_str))
    # The cf_name_table.txt index, the frequency, number of
    # transformation, coupling restart file and EXPORTED/EXPOUT
    nam_file.write('%d %d %d %s  %s\n' % \
                       (cf_table_number, cpl_freq, n_trans,
                        cpl_restart_file, exp_type))

def _write_grid_info(nam_file, ocn_abrev, nam_entry, seq,
                     run_info, l_rmp_create):
    '''
    Write the grid information to namcouple file
    '''

    # Determine the grid names
    if nam_entry.origin == 'OCN' or nam_entry.dest == 'OCN':
        # We'll need a land-sea mask for this
        origin_grid = ATM2OCN_GRIDS[nam_entry.origin][nam_entry.grid]
        dest_grid = ATM2OCN_GRIDS[nam_entry.dest][nam_entry.grid]
        if nam_entry.origin == 'OCN':
            origin_overlap = 2
            dest_overlap = 0
        else:
            origin_overlap = 0
            dest_overlap = 2
    else:
        # SNR<->JNR coupling
        origin_overlap = 0
        dest_overlap = 0
        if nam_entry.origin == 'JNR':
            origin_start = 'j'
            dest_start = 's'
        else:
            origin_start = 's'
            dest_start = 'j'

        # Soil/land fields require a mask
        if nam_entry.l_soil:
            mid_name = ocn_abrev
        else:
            mid_name = 'nr'

        # Put parts of the grid names together
        origin_grid = origin_start + mid_name + nam_entry.grid
        dest_grid = dest_start + mid_name + nam_entry.grid

    # Scalar passing has very different arguments
    if nam_entry.mapping == 'Scalar':
        # Write the resolutions and grids
        nam_file.write(' 1 1 1 1 %s %s SEQ=+%d\n' % \
                           (origin_grid, dest_grid, seq))

        # Write the rest of the information
        nam_file.write(' R 0 R 0\n#\n BLASOLD\n#\n 1.0 0\n')
    elif nam_entry.mapping == 'OneD':
        # Determine resolution
        if origin_grid in run_info:
            data_len = run_info[origin_grid]
        else:
            sys.stderr.write('[FAIL] size of 1d grid %s is unknown.\n' %
                             origin_grid)
            sys.exit(error.UNKNOWN_1D_GRID_SIZE)
        # Write the resolutions and grids
        nam_file.write(' %d 1 %d 1 %s %s SEQ=+%d\n' % \
                       (data_len, data_len, origin_grid, dest_grid, seq))

        # Write the rest of the information
        nam_file.write(' R 0 R 0\n#\n BLASOLD\n#\n 1.0 0\n')
    else:
        # Determine the number of grid points in y-direction
        origin_resol_name = nam_entry.origin + '_resol'
        dest_resol_name = nam_entry.dest + '_resol'
        ny_origin = run_info[origin_resol_name][1]
        if nam_entry.grid == 'v' and (nam_entry.origin == 'ATM' or
                                      nam_entry.origin == 'JNR'):
            # An extra grid point is needed for atmosphere on v-grid.
            ny_origin += 1
        ny_dest = run_info[dest_resol_name][1]
        if nam_entry.grid == 'v' and (nam_entry.dest == 'ATM' or
                                      nam_entry.dest == 'JNR'):
            # An extra grid point is needed for atmosphere on v-grid.
            ny_dest += 1

        # Write the resolutions and grids
        nam_file.write(' %d %d %d %d %s %s SEQ=+%d\n' % \
                           (run_info[origin_resol_name][0], ny_origin,
                            run_info[dest_resol_name][0], ny_dest,
                            origin_grid, dest_grid, seq))

        # For now we're always using periodic boundary conditions
        nam_file.write(' P %d P %d\n' % (origin_overlap, dest_overlap))

        if l_rmp_create:
            # Create the rmp file
            nam_file.write('#\n LOCTRANS SCRIPR\n INSTANT\n')

            if nam_entry.mapping == 'CONSERV_DESTAREA':
                nam_file.write(' CONSERV LR SCALAR LATLON 50 DESTAREA ')
                if nam_entry.mapping_type == 2:
                    nam_file.write('SECOND\n')
                else:
                    nam_file.write('FIRST\n')
            elif nam_entry.mapping == 'CONSERV_FRACAREA':
                nam_file.write(' CONSERV LR SCALAR LATLON 50 FRACAREA ')
                if nam_entry.mapping_type == 2:
                    nam_file.write('SECOND\n')
                else:
                    nam_file.write('FIRST\n')
            elif nam_entry.mapping == 'BILINEA' or \
                    nam_entry.mapping == 'BILINEAR':
                nam_file.write(' BILINEAR LR SCALAR LATLON 1\n')
            elif nam_entry.mapping == 'BICUBIC':
                nam_file.write(' BICUBIC LR SCALAR LATLON 1\n')
            else:
                sys.stderr.write('[FAIL] unable to create remapping file for '
                                 'mapping of %s\n' % nam_entry.mapping)
                sys.exit(error.MISSING_RMP_MAPPING)
        else:
            # See if we require postproc conservation
            if nam_entry.mapping.find('-') > 0:
                l_postproc_conserv = True
                (mapping, conserv_method) = nam_entry.mapping.split('-')
                # MAPPING text
                nam_file.write('#\n MAPPING CONSERV\n#\n')
            else:
                l_postproc_conserv = False
                mapping = nam_entry.mapping
                # MAPPING text
                nam_file.write('#\n MAPPING\n#\n')

            # Remapping file
            nam_file.write(' rmp_%s_to_%s_%s' % \
                               (origin_grid, dest_grid, mapping))
            if nam_entry.mapping.count('CONSERV') >= 1:
                if nam_entry.mapping_type == 2:
                    nam_file.write('_2nd.nc\n')
                else:
                    nam_file.write('_1st.nc\n')
            else:
                nam_file.write('.nc\n')

            if l_postproc_conserv:
                # Extra line with postproc conservation method required
                nam_file.write(' %s\n' % conserv_method)

def write_namcouple_fields(nam_file, run_info, coupling_list):
    '''
    Write the fields in coupling_list to namcouple file
    '''
    # Determine the abreviated ocean name used for the SNR<->JNR
    # coupling grids
    if 'OCN_grid' in run_info:
        ocn_res = int(run_info['OCN_grid'].replace('orca', ''))
        if ocn_res < 10:
            ocn_abrev = 'o' + str(ocn_res)
        else:
            ocn_abrev = str(ocn_res)
    else:
        # The problem is likely to be that this is a SNR<->JNR
        # coupling without an ocean, and so the ocean resolution
        # which is used in all the ancillaries etc needed to be
        # explicitly defined in the um app.
        sys.stderr.write('[FAIL] ocean resolution will need to be set. '
                         'Try setting the environment variable OCN_RES '
                         'in the um app.\n')
        sys.exit(error.NO_OCN_RESOL)

    # Initialise
    origin_old = 'none'
    seq = 0
    n_field = 1
    cf_names = []
    cf_table_num = {}
    n_cf_table = 0
    cpl_restart_file = 'atmos_restart.nc'
    stashmaster_info = None

    # Loop across all the coupling
    for nam_entry in coupling_list:

        # Determine if field should be removed
        if nam_entry.mapping != 'remove':

            # Determine if seq should be updated
            if nam_entry.origin != origin_old:
                seq += 1
                origin_old = nam_entry.origin

            # Determine the coupling frequency
            cpl_freq = _coupling_freq(nam_entry, run_info)

            # Determine if this is a hybrid field
            if nam_entry.l_hybrid:
                # Determine if STASHmaster_A file should be read
                if not stashmaster_info:
                    stashmaster_info = \
                        _read_stashmaster(run_info['STASHMASTER'])

                # Determine the base name_in, long name, grid and number
                # of vertical levels
                name_in, longname, nam_entry.grid, \
                    nam_entry.nlev, nam_entry.l_soil = \
                    _snr2jnr_field_info(nam_entry,
                                        run_info['ATM_model_levels'],
                                        run_info['ATM_soil_levels'],
                                        run_info['ATM_veg_tiles'],
                                        run_info['ATM_non_veg_tiles'],
                                        stashmaster_info)

                # Determine the cf_name_table.txt attributes
                cf_names.append(
                    write_cf_name_table.CfNameTableEntry(longname, 'unknown'))
                n_cf_table += 1
                cf_table_number = n_cf_table

            else:
                # Determine further field information
                name_in, cf_names, cf_table_number, cf_table_num, n_cf_table = \
                    _atm2ocn_field_info(nam_entry, cf_names, cf_table_num,
                                        n_cf_table)
                longname = cf_names[cf_table_number - 1].longname

            # See if remapping file needs creating
            l_rmp_create = False
            n_trans = 1
            if 'rmp_create' in run_info:
                if nam_entry.l_hybrid:
                    name_match_str = nam_entry.name_out[0:6]
                else:
                    name_match_str = nam_entry.name_out
                for create_entry in run_info['rmp_create']:
                    if create_entry == name_match_str:
                        l_rmp_create = True
                        n_trans += 1

            # Transformation are also increased by postproc conservation
            if nam_entry.mapping.find('-') > 0 and n_trans == 1:
                n_trans = 2

            # Write the TRANSDEF information to namcouple
            _write_transdef(nam_file, nam_entry, cpl_freq, n_field, longname)

            # Write the line with field names and coupling frequency
            _write_main_line(nam_file, nam_entry, cpl_freq, name_in,
                             cf_table_number, n_trans, cpl_restart_file,
                             run_info)

            # Write the grid information
            _write_grid_info(nam_file, ocn_abrev, nam_entry, seq,
                             run_info, l_rmp_create)

            # Move to next field
            n_field += 1

    return cf_names
