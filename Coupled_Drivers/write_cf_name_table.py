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
    write_cf_name_table.py

DESCRIPTION
    Write the CF name table, cf_name_table.txt, at run time.
'''
import common

# The long names and units used in cf_name_table.txt
CF_ATTR = {'_MSLP':['air_pressure_at_mean_sea_level', 'Pa'],
           '_OCurx1':['surface_grid_eastward_sea_water_velocity', 'm s-1'],
           '_OCury1':['surface_grid_northward_sea_water_velocity', 'm s-1'],
           '_QnsOce':['surface_downward_non_shortwave_heat_flux', 'W m-2'],
           '_QsrOce':['surface_net_downward_shortwave_flux', 'W m-2'],
           '_OTaux1':['surface_downward_grid_eastward_stress', 'Pa'],
           '_OTauy1':['surface_downward_grid_northward_stress', 'Pa'],
           '_Runoff':['water_flux_into_ocean_from_rivers', 'kg m-2 s-1'],
           '_SSTSST':['sea_surface_temperature', 'K'],
           '_TtiLyr':['ice_conductivity', 'W m-1 K-1'],
           '_Wind10':['wind_speed_at_10m', 'm s-1'],
           'Antmass':['Antarctica_ice_mass', 'kg'],
           'ATMDUST':['Total_dust_deposition_rate', 'kg m-2 s-1'],
           'ATMPCO2':['Surface_level_of_CO2_tracer', 'mmr'],
           'BioChlo':['Ocean_near_surface_chlorophyll', 'kg m-3'],
           'BioCO2':['CO2_ocean_flux', 'kg m-2 s-1'],
           'BioDMS':['DMS_concentration_in_seawater', 'umol m-3'],
           'BotMlt':['Multi-category_Fcondtop', 'W m-2'],
           'Grnmass':['Greenland_ice_mass', 'kg'],
           'IceEvap':['Multi-category_water_evaporation_flux_where_sea_ice',
                      'kg m-2 s-1'],
           'IceEvp':['Multi-category_water_evaporation_flux_where_sea_ice',
                     'kg m-2 s-1'],
           'IceFrc':['sea_ice_area_fraction', '1'],
           'IceFrd':['sea_ice-1st_order_regridded_ice_conc', '1'],
           'IceKn':['Multi-category sfc ice layer effective conductivity',
                    'W m-2 deg-1'],
           'IceTck':['Multi-category_ice_thickness', 'm'],
           'PndFrc':['Melt_pond_fraction', '1'],
           'PndTck':['Mean_melt_pond_depth', 'Pa'],
           'Qtr':['Transmitted solar', 'W m-2'],
           'Runff1D':['water_flux_into_ocean_from_rivers', 'kg m-2 s-1'],
           'SnwTck':['surface_snow_amount', 'kg m-2'],
           'TepIce':['Multi-category_sfc_ice_layer_temperature', 'K'],
           'TopMlt':['Multi-category_Topmelt', 'W m-2'],
           'TotEvap':['water_evaporation_flux', '1'],
           'TotRain':['rainfall_flux', 'kg m-2 s-1'],
           'TotSnow':['snow_fall_flux', 'kg m-2 s-1'],
           'TsfIce':['Sea_ice_surface_skin_temperature', 'C']}

class CfNameTableEntry():
    '''
    Container to hold the information for one entry in cf_name_table.txt
    '''

    def __init__(self, longname, unit):
        self.longname = longname
        self.unit = unit

    def __repr__(self):
        return repr((self.longname, self.unit))

def write_cf_name_table(cf_names):
    '''
    Write the cf_name_table.txt file
    '''
    # Open the file
    cf_file = common.open_text_file('cf_name_table.txt', 'w')

    # Write the header
    cf_file.write('# Maximum index of the table entries, total '
                  'number of indices\n')
    cf_file.write('%d %d\n' % (len(cf_names), len(cf_names)))
    cf_file.write('#Index, CF longname, unit\n')

    # Loop across the entries
    i_entry = 1
    for cf_entry in cf_names:
        cf_file.write(" %d  '%s' '%s'\n" % (i_entry, cf_entry.longname,
                                            cf_entry.unit))
        i_entry += 1

    # Close file
    cf_file.close()
