#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2024 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    filenames.py

DESCRIPTION
    Regular expressions describing all filenames to be fouind in the archive
'''

import re

FIELD_REGEX = r'[a-zA-Z0-9\-]*'

MODEL_COMPONENTS = {
    # Key=model name
    # Value=tuple(realm, dict(fields associated with netCDF model component(s)))
    'atmos': {'atmos': ('a', [FIELD_REGEX], [''])},
    'nemo': {'nemo': ('o', ['grid-U', 'grid-V', 'grid-W', 'grid-T',
                            'diaptr', 'trnd3d', 'scalar',
                            'UK-shelf-T', 'UK-shelf-U', 'UK-shelf-V'],
                      ['', 'icebergs']),
             'medusa': ('o', ['ptrc-T', 'diad-T', 'ptrd-T'], ['ptracer']),
             'si3': ('i', ['icemod'], ['ice'])},
    'cice': {'cice': ('i', '', ['', 'age'])},
    }

FNAMES = {
    # Please note: Restart file keys MUST end with "_rst",
    # and match the associated namelist logical name
    'atmos_rst': r'{P}a.da{Y1:04d}{M1:02d}{D1:02d}_00',
    'atmos_pp': r'{P}a.{CF}{Y1}{M1}{D1}{H1}.pp',
    'atmos_ff': r'{P}a.{CF}{Y1}{M1}{D1}{H1}',
    'atmos_ozone': r'{P}a.{CF}{Y1}.pp',

    'cice_rst': r'{P}i.restart.{Y1:04d}-{M1:02d}-{D1:02d}-00000{S}',
    'cice_age_rst': r'{P}i.restart.age.{Y1:04d}-{M1:02d}-{D1:02d}-00000{S}',

    'nemo_rst': r'{P}o_{Y1:04d}{M1:02d}{D1:02d}_restart.nc',
    'nemo_ice_rst': r'{P}o_{Y1:04d}{M1:02d}{D1:02d}_restart_ice.nc',
    'nemo_icebergs_rst': r'{P}o_icebergs_{Y1:04d}{M1:02d}{D1:02d}_restart.nc',
    'nemo_icb_rst': r'{P}o_{Y1:04d}{M1:02d}{D1:02d}_restart_icb.nc',
    'nemo_ptracer_rst': r'{P}o_{Y1:04d}{M1:02d}{D1:02d}_restart_trc.nc',
    'nemo_ibergs_traj': r'{P}o_trajectory_icebergs_{TS}.nc',

    'ncf_mean': r'{CM}_{P}{R}_{F}_{Y1}{M1}{D1}{H1}-{Y2}{M2}{D2}{H2}{CF}.nc',
    }

COLLECTIONS = {
    'rst': r'{R}da.file',
    'atmos_pp': r'a{S}.pp',
    'atmos_ff': r'a{S}.file',
    'atmos_ozone': r'a{S}.pp',
    'ncf_mean': r'{R}n{S}.nc.file',
    }


def model_components(model, field):
    ''' Return realm and model component for given model and field '''
    realm = MODEL_COMPONENTS[model][model][0]
    component = None
    if str(field).endswith('_rst'):
        # Restart files
        rsttype = field.lstrip(model).rstrip('rst').strip('_')
        for comp in MODEL_COMPONENTS[model]:
            if rsttype in MODEL_COMPONENTS[model][comp][2]:
                realm = MODEL_COMPONENTS[model][comp][0]
                break
    elif re.match('^[pm][a-z0-9]$', str(field)):
        # Atmosphere 2char fields
        pass
    else:
        # netCDF file - component required.  Initialise with model name.
        component = model
        for comp in MODEL_COMPONENTS[model]:
            if field in MODEL_COMPONENTS[model][comp][1]:
                component = comp
                realm = MODEL_COMPONENTS[model][comp][0]
                break

    return realm, component
