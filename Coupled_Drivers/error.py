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
    error.py

DESCRIPTION
    Module containing error codes for the drivers. To ensure consistancy over
    all the scripts that will make up the drivers, it is recommended that the
    follwing error codes be used for self consistancy. Any error codes <100
    are to be used within the drivers themselves, for specific errors.
'''
# Python errors
VERSION_ERROR = 1

# Import Error
IMPORT_ERROR = 2

# File I/O errors
IOERROR = 100

# Missing Environment variable
MISSING_EVAR_ERROR = 101

# Subprocess Error
SUBPROC_ERROR = 102

# Invalid environment variable
INVALID_EVAR_ERROR = 103

# Date matching error
DATE_MISMATCH_ERROR = 104

# Invalid local variable
INVALID_LOCAL_ERROR = 110

# Missing Driver
MISSING_DRIVER_ERROR = 200

# Missing file required by a driver
MISSING_DRIVER_FILE_ERROR = 201

# Invalid argument to driver script
INVALID_DRIVER_ARG_ERROR = 202

# Missing file required by a controller
MISSING_CONTROLLER_FILE_ERROR = 251

# Type conversion error
TYPE_COVERSION_ERROR = 300

# Missing file that will be required by a component model
MISSING_MODEL_FILE_ERROR = 400

# Corrupted file that will be required by a component model
CORRUPTED_MODEL_FILE_ERROR = 401

# An error in the component model
COMPONENT_MODEL_ERROR = 402

# Restart file time does not match length of run
RESTART_FILE_ERROR = 403

# Invalid function argument
INVALID_FUNC_ARG_ERROR = 500

# Invalid component version
INVALID_COMPONENT_VER_ERROR = 600

# Restart date error
MISMATCH_RESTART_DATE_ERROR = 700

# The errors between 800 and 899 are all to do with creating the
# namcouple on the fly.
# The following errors relate to the following files
#  - 800:     link_drivers
#  - 801-809: write_namcouple.py
#  - 810-819: write_namcouple_fields.py
#  - 820-829: mct_driver.py
#  - 830-839: nemo_driver.py
#  - 840-859: um_driver.py
#  - 860-869: jnr_driver.py
#  - 870-879: default_couplings.py

# f90nml python module is unavailable
F90NML_UNAVAILABLE = 800

# Missing namcouple input
MISSING_NAMCOUPLE_INPUT = 801

# Unrecognised mapping for namcouple file
UNRECOGNISED_MAPPING = 802

# Need to define at least the first mapping for series of
# coupling fields
MISSING_MAPPING = 803

# Need to define at least the first weighting for series of
# coupling fields
MISSING_WEIGHTING = 804

# Coupling entry looks to be in the wrong format
WRONG_CPL_FORMAT = 805

# Model levels for Snr and Jnr are different
DIFFERENT_MODEL_LEVELS = 806

# Soil levels for Snr and Jnr are different
DIFFERENT_SOIL_LEVELS = 809

# Not found couping variable in run_info
NOT_FOUND_CPL_VAR = 810

# Not enough coupling frequencies
NOT_ENOUGH_CPL_FREQ = 811

# Missing the STASHmaster_A file
MISSING_STASHMASTER_A = 812

# Unrecognised grid
UNRECOGNISED_GRID = 813

# Unrecognised levelF or levelL
UNRECOGNISED_LEVEL = 814

# Not found the stash code in stashmaster_info
NOT_FOUND_STASH_CODE = 815

# Unable to create remapping file for mapping type
MISSING_RMP_MAPPING = 816

# Ocean resolution for Snr<->Jnr coupling is not specified
NO_OCN_RESOL = 818

# Not found SHARED file
NOT_FOUND_SHARED = 820

# Unrecognised coupling components
UNRECOGNISED_COMP = 821

# Coupling variable is not defined
UNRECOGNISED_CPL_VAR = 822

# Missing coupling_control namelist in SHARED
MISSING_CPL_CONTROL = 823

# Missing coupling frequency
MISSING_CPL_FREQ = 824

# Can't find the core remapping directory
MISSING_CORE_RMP_DIR = 825

# Can't find the core remapping file
MISSING_CORE_RMP_FILE = 826

# Missing grid information in run_info
MISSING_GRID_IN_RUN_INFO = 827

# Missing a remapping weights directory
MISSING_RMP_DIR = 828

# Missing OASIS send file for ocean
MISSING_OASIS_OCN_SEND = 830

# Missing the ocean resolution namelist
MISSING_OCN_RESOL_NML = 831

# Missing the ocean resolution parameters
MISSING_OCN_RESOL = 832

# Not on ORCA grid
NOT_ORCA_GRID = 833

# Not declared ocean resolution when creating namcouple on fly after NEMO3.6
NOT_DECLARE_OCN_RES = 834

# Unknown ocean resolution
UNKNOWN_OCN_RESOL = 835

# Missing namelist oasis_ocn_send_nml from OASIS_OCN_SEND
MISSING_OASIS_OCN_SEND_NML = 836

# Missing entry oasis_ocn_send from namelist oasis_ocn_send_nml
MISSING_OASIS_OCN_SEND = 837

# Missing OASIS send file for UM
MISSING_OASIS_ATM_SEND = 840

# Missing a SIZES file
MISSING_FILE_SIZES = 841

# Missing namelist
MISSING_ATM_RESOL_NML = 842

# Missing namelist oasis_send_nml from OASIS_ATM_SEND
MISSING_OASIS_SEND_NML_ATM = 843

# Missing default remapping in hybrid_rmp_mapping variable
MISSING_DEFAULT_RMP = 844

# Missing entry 'hybrid_weight' from namelist
# oasis_atm_send_nml/oasis_jnr_send_nml
MISSING_HYBRID_WEIGHT = 845

# Missing entry 'hybrid_rmp_mapping' from namelist
# oasis_atm_send_nml/oasis_jnr_send_nml
MISSING_HYBRID_RMP_MAPPING = 846

# Missing hybrid namelist
MISSING_HYBRID_NML = 847

# Missing coupling fields in hybrid namelist
MISSING_HYBRID_SEND = 848

# Missing nlsizes namelist from SIZES file
MISSING_ATM_RESOL_NML = 849

# Missing 'global_row_length' or 'global_rows' from nlsizes namelist
MISSING_ATM_HORIZ_RESOL = 850

# Missing 'model_levels' from nlsizes namelist
MISSING_ATM_VERT_RESOL = 851

# Missing a SHARED file
MISSING_FILE_SHARED = 852

# Missing JULES namelist
MISSING_JULES_RESOL_NML = 853

# Missing the soil depths array
MISSING_JULES_VERT_RESOL = 854

# Missing tile information
MISSING_JULES_TILE_INFO = 855

# Missing OASIS send file for Jnr UM
MISSING_OASIS_JNR_SEND = 860

# Missing namelist oasis_jnr_send_nml from OASIS_JNR_SEND
MISSING_OASIS_SEND_NML_JNR = 861

# Missing entry oasis_jnr_send from namelist oasis_jnr_send_nml
MISSING_OASIS_JNR_SEND = 862

# Don't have a default option for this
MISSING_DEFAULT_OPTION = 870

# Not found the coupling namelist in namelist_cfg
MISSING_NAMSBC_CPL = 871
