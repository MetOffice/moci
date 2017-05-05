#!/usr/bin/env bash

###############################################################################
# check_output.sh
#
# Purpose:  
#    To parse the job-archive.jog files ensure all has been archived 
#    which should have been archived
#
# Required Environment:
#
# Updates:
#   MOCI #62  - Moved start date to October to test acceptance of spinup period 
#               for means
#             - Removed archived files:
#                  hg3esa.da19811001_00
#                  hg3esa.ph19810901
#                  hg3esa.ph19810911
#                  hg3esa.ph19810921
#                  hg3esa.pj19810901
#                  hg3esa.pm1981sep
#                  hg3esi.1m.1981-09.nc
#                  hg3esi.1s.1981-11.nc
#                  hg3eso_1m_19810901_19810930_grid_V.nc
#                  hg3eso_1s_19810901_19811130_grid_V.nc
#   MOCI #94  - Change to the datestamp format for the CICE seasonal and 
#               annual means
#             - hg3esi.is.YYY2-M2.nc -> hg3esi.1s.YYY1-M1_YYY2-M2.nc
#             - hg3esi.iy.YYY2-11.nc -> hg3esi.1y.YYY1-12_YYY2-11.nc
#   MOCI #108 - Change to NEMO/CICE output filenames in accordance with
#               filenaming convention
#   MOCI #130 - Added additional files archived in final cycle
#               - hg3esa.ph19830101.pp, hg3esa.ph19830111.pp, hg3esa.ph19830121.pp
#               - hg3eso_1m_19821201_19821230_grid_V.nc, hg3eso_1m_19830101_19830130_grid_V.nc
#               - hg3esi.1m.1982-12.nc, hg3esi.1m.1983-01.nc
#             - Added checks to ensure final restart files, incomplete fieldsfiles and
#               components for future higher means remain on disk
#               - hg3esa.da19830201_00, hg3esa.ph19830121, hg3esa.pj19821201
#               - hg3eso_1m_19821201_19821230_grid_V.nc, hg3eso_1m_19830101_19830130_grid_V.nc,
#                hg3eso_19830230_restart.nc, hg3eso_19830230_restart_0000.nc,
#                hg3eso_19830230_restart_0001.nc, hg3eso_19830230_restart_0002.nc
#               - hg3esi.1m.1982-12.nc, hg3esi.1m.1983-01.nc, hg3esi.restart.1983-02-01-00000
#   MOCI #150 - Added processing of 10hr a.pe stream.
#                - "archive_as_fieldsfile" stream changed from a.pj to a.pe
#                - Atmosphere archiving frequency changed to seasonal
#   MOCI #184 - Changed the mean reference time for NEMOCICE means to Jan 1st
#               Turned off NEMO monthly and annual means production
#   MOCI #138   - No attempt is being made to process (archive or convert) empty files when
#                 using Mule to verify the header.  
#                 In the interests of continuing to test functionality, we'll assume that
#                 they've been archived based on presence of _ARCHIVED files, but conversion
#                 to pp has been disabled.
#
###############################################################################

adumps="
hg3esa.da19811201_00
hg3esa.da19820301_00
hg3esa.da19820601_00
hg3esa.da19820901_00
hg3esa.da19821201_00
hg3esa.da19830201_00"

apm="
hg3esa.pm1981oct.pp
hg3esa.pm1981nov.pp
hg3esa.pm1981dec.pp
hg3esa.pm1982jan.pp
hg3esa.pm1982feb.pp
hg3esa.pm1982mar.pp
hg3esa.pm1982apr.pp
hg3esa.pm1982may.pp
hg3esa.pm1982jun.pp
hg3esa.pm1982jul.pp
hg3esa.pm1982aug.pp
hg3esa.pm1982sep.pp
hg3esa.pm1982oct.pp
hg3esa.pm1982nov.pp
hg3esa.pm1982dec.pp"

aps="
hg3esa.ps1982djf.pp
hg3esa.ps1982mam.pp
hg3esa.ps1982jja.pp
hg3esa.ps1982son.pp"

apy="hg3esa.py19821201.pp"

ape="
hg3esa.pe19811001_00
hg3esa.pe19811001_10
hg3esa.pe19811001_20
hg3esa.pe19811002_06
hg3esa.pe19811002_16
hg3esa.pe19811003_02
hg3esa.pe19811003_12
hg3esa.pe19811003_22
hg3esa.pe19811004_08
hg3esa.pe19811004_18
hg3esa.pe19811005_04
hg3esa.pe19811005_14
hg3esa.pe19811006_00
hg3esa.pe19811006_10
hg3esa.pe19811006_20
hg3esa.pe19811007_06
hg3esa.pe19811007_16
hg3esa.pe19811008_02
hg3esa.pe19811008_12
hg3esa.pe19811008_22
hg3esa.pe19811009_08
hg3esa.pe19811009_18
hg3esa.pe19811010_04
hg3esa.pe19811010_14
hg3esa.pe19811011_00
hg3esa.pe19811011_10
hg3esa.pe19811011_20
hg3esa.pe19811012_06
hg3esa.pe19811012_16
hg3esa.pe19811013_02
hg3esa.pe19811013_12
hg3esa.pe19811013_22
hg3esa.pe19811014_08
hg3esa.pe19811014_18
hg3esa.pe19811015_04
hg3esa.pe19811015_14
hg3esa.pe19811016_00
hg3esa.pe19811016_10
hg3esa.pe19811016_20
hg3esa.pe19811017_06
hg3esa.pe19811017_16
hg3esa.pe19811018_02
hg3esa.pe19811018_12
hg3esa.pe19811018_22
hg3esa.pe19811019_08
hg3esa.pe19811019_18
hg3esa.pe19811020_04
hg3esa.pe19811020_14
hg3esa.pe19811021_00
hg3esa.pe19811021_10
hg3esa.pe19811021_20
hg3esa.pe19811022_06
hg3esa.pe19811022_16
hg3esa.pe19811023_02
hg3esa.pe19811023_12
hg3esa.pe19811023_22
hg3esa.pe19811024_08
hg3esa.pe19811024_18
hg3esa.pe19811025_04
hg3esa.pe19811025_14
hg3esa.pe19811026_00
hg3esa.pe19811026_10
hg3esa.pe19811026_20
hg3esa.pe19811027_06
hg3esa.pe19811027_16
hg3esa.pe19811028_02
hg3esa.pe19811028_12
hg3esa.pe19811028_22
hg3esa.pe19811029_08
hg3esa.pe19811029_18
hg3esa.pe19811030_04
hg3esa.pe19811030_14
hg3esa.pe19811101_00
hg3esa.pe19811101_10
hg3esa.pe19811101_20
hg3esa.pe19811102_06
hg3esa.pe19811102_16
hg3esa.pe19811103_02
hg3esa.pe19811103_12
hg3esa.pe19811103_22
hg3esa.pe19811104_08
hg3esa.pe19811104_18
hg3esa.pe19811105_04
hg3esa.pe19811105_14
hg3esa.pe19811106_00
hg3esa.pe19811106_10
hg3esa.pe19811106_20
hg3esa.pe19811107_06
hg3esa.pe19811107_16
hg3esa.pe19811108_02
hg3esa.pe19811108_12
hg3esa.pe19811108_22
hg3esa.pe19811109_08
hg3esa.pe19811109_18
hg3esa.pe19811110_04
hg3esa.pe19811110_14
hg3esa.pe19811111_00
hg3esa.pe19811111_10
hg3esa.pe19811111_20
hg3esa.pe19811112_06
hg3esa.pe19811112_16
hg3esa.pe19811113_02
hg3esa.pe19811113_12
hg3esa.pe19811113_22
hg3esa.pe19811114_08
hg3esa.pe19811114_18
hg3esa.pe19811115_04
hg3esa.pe19811115_14
hg3esa.pe19811116_00
hg3esa.pe19811116_10
hg3esa.pe19811116_20
hg3esa.pe19811117_06
hg3esa.pe19811117_16
hg3esa.pe19811118_02
hg3esa.pe19811118_12
hg3esa.pe19811118_22
hg3esa.pe19811119_08
hg3esa.pe19811119_18
hg3esa.pe19811120_04
hg3esa.pe19811120_14
hg3esa.pe19811121_00
hg3esa.pe19811121_10
hg3esa.pe19811121_20
hg3esa.pe19811122_06
hg3esa.pe19811122_16
hg3esa.pe19811123_02
hg3esa.pe19811123_12
hg3esa.pe19811123_22
hg3esa.pe19811124_08
hg3esa.pe19811124_18
hg3esa.pe19811125_04
hg3esa.pe19811125_14
hg3esa.pe19811126_00
hg3esa.pe19811126_10
hg3esa.pe19811126_20
hg3esa.pe19811127_06
hg3esa.pe19811127_16
hg3esa.pe19811128_02
hg3esa.pe19811128_12
hg3esa.pe19811128_22
hg3esa.pe19811129_08
hg3esa.pe19811129_18
hg3esa.pe19811130_04
hg3esa.pe19811130_14
hg3esa.pe19811201_00
hg3esa.pe19811201_10
hg3esa.pe19811201_20
hg3esa.pe19811202_06
hg3esa.pe19811202_16
hg3esa.pe19811203_02
hg3esa.pe19811203_12
hg3esa.pe19811203_22
hg3esa.pe19811204_08
hg3esa.pe19811204_18
hg3esa.pe19811205_04
hg3esa.pe19811205_14
hg3esa.pe19811206_00
hg3esa.pe19811206_10
hg3esa.pe19811206_20
hg3esa.pe19811207_06
hg3esa.pe19811207_16
hg3esa.pe19811208_02
hg3esa.pe19811208_12
hg3esa.pe19811208_22
hg3esa.pe19811209_08
hg3esa.pe19811209_18
hg3esa.pe19811210_04
hg3esa.pe19811210_14
hg3esa.pe19811211_00
hg3esa.pe19811211_10
hg3esa.pe19811211_20
hg3esa.pe19811212_06
hg3esa.pe19811212_16
hg3esa.pe19811213_02
hg3esa.pe19811213_12
hg3esa.pe19811213_22
hg3esa.pe19811214_08
hg3esa.pe19811214_18
hg3esa.pe19811215_04
hg3esa.pe19811215_14
hg3esa.pe19811216_00
hg3esa.pe19811216_10
hg3esa.pe19811216_20
hg3esa.pe19811217_06
hg3esa.pe19811217_16
hg3esa.pe19811218_02
hg3esa.pe19811218_12
hg3esa.pe19811218_22
hg3esa.pe19811219_08
hg3esa.pe19811219_18
hg3esa.pe19811220_04
hg3esa.pe19811220_14
hg3esa.pe19811221_00
hg3esa.pe19811221_10
hg3esa.pe19811221_20
hg3esa.pe19811222_06
hg3esa.pe19811222_16
hg3esa.pe19811223_02
hg3esa.pe19811223_12
hg3esa.pe19811223_22
hg3esa.pe19811224_08
hg3esa.pe19811224_18
hg3esa.pe19811225_04
hg3esa.pe19811225_14
hg3esa.pe19811226_00
hg3esa.pe19811226_10
hg3esa.pe19811226_20
hg3esa.pe19811227_06
hg3esa.pe19811227_16
hg3esa.pe19811228_02
hg3esa.pe19811228_12
hg3esa.pe19811228_22
hg3esa.pe19811229_08
hg3esa.pe19811229_18
hg3esa.pe19811230_04
hg3esa.pe19811230_14
hg3esa.pe19820101_00
hg3esa.pe19820101_10
hg3esa.pe19820101_20
hg3esa.pe19820102_06
hg3esa.pe19820102_16
hg3esa.pe19820103_02
hg3esa.pe19820103_12
hg3esa.pe19820103_22
hg3esa.pe19820104_08
hg3esa.pe19820104_18
hg3esa.pe19820105_04
hg3esa.pe19820105_14
hg3esa.pe19820106_00
hg3esa.pe19820106_10
hg3esa.pe19820106_20
hg3esa.pe19820107_06
hg3esa.pe19820107_16
hg3esa.pe19820108_02
hg3esa.pe19820108_12
hg3esa.pe19820108_22
hg3esa.pe19820109_08
hg3esa.pe19820109_18
hg3esa.pe19820110_04
hg3esa.pe19820110_14
hg3esa.pe19820111_00
hg3esa.pe19820111_10
hg3esa.pe19820111_20
hg3esa.pe19820112_06
hg3esa.pe19820112_16
hg3esa.pe19820113_02
hg3esa.pe19820113_12
hg3esa.pe19820113_22
hg3esa.pe19820114_08
hg3esa.pe19820114_18
hg3esa.pe19820115_04
hg3esa.pe19820115_14
hg3esa.pe19820116_00
hg3esa.pe19820116_10
hg3esa.pe19820116_20
hg3esa.pe19820117_06
hg3esa.pe19820117_16
hg3esa.pe19820118_02
hg3esa.pe19820118_12
hg3esa.pe19820118_22
hg3esa.pe19820119_08
hg3esa.pe19820119_18
hg3esa.pe19820120_04
hg3esa.pe19820120_14
hg3esa.pe19820121_00
hg3esa.pe19820121_10
hg3esa.pe19820121_20
hg3esa.pe19820122_06
hg3esa.pe19820122_16
hg3esa.pe19820123_02
hg3esa.pe19820123_12
hg3esa.pe19820123_22
hg3esa.pe19820124_08
hg3esa.pe19820124_18
hg3esa.pe19820125_04
hg3esa.pe19820125_14
hg3esa.pe19820126_00
hg3esa.pe19820126_10
hg3esa.pe19820126_20
hg3esa.pe19820127_06
hg3esa.pe19820127_16
hg3esa.pe19820128_02
hg3esa.pe19820128_12
hg3esa.pe19820128_22
hg3esa.pe19820129_08
hg3esa.pe19820129_18
hg3esa.pe19820130_04
hg3esa.pe19820130_14
hg3esa.pe19820201_00
hg3esa.pe19820201_10
hg3esa.pe19820201_20
hg3esa.pe19820202_06
hg3esa.pe19820202_16
hg3esa.pe19820203_02
hg3esa.pe19820203_12
hg3esa.pe19820203_22
hg3esa.pe19820204_08
hg3esa.pe19820204_18
hg3esa.pe19820205_04
hg3esa.pe19820205_14
hg3esa.pe19820206_00
hg3esa.pe19820206_10
hg3esa.pe19820206_20
hg3esa.pe19820207_06
hg3esa.pe19820207_16
hg3esa.pe19820208_02
hg3esa.pe19820208_12
hg3esa.pe19820208_22
hg3esa.pe19820209_08
hg3esa.pe19820209_18
hg3esa.pe19820210_04
hg3esa.pe19820210_14
hg3esa.pe19820211_00
hg3esa.pe19820211_10
hg3esa.pe19820211_20
hg3esa.pe19820212_06
hg3esa.pe19820212_16
hg3esa.pe19820213_02
hg3esa.pe19820213_12
hg3esa.pe19820213_22
hg3esa.pe19820214_08
hg3esa.pe19820214_18
hg3esa.pe19820215_04
hg3esa.pe19820215_14
hg3esa.pe19820216_00
hg3esa.pe19820216_10
hg3esa.pe19820216_20
hg3esa.pe19820217_06
hg3esa.pe19820217_16
hg3esa.pe19820218_02
hg3esa.pe19820218_12
hg3esa.pe19820218_22
hg3esa.pe19820219_08
hg3esa.pe19820219_18
hg3esa.pe19820220_04
hg3esa.pe19820220_14
hg3esa.pe19820221_00
hg3esa.pe19820221_10
hg3esa.pe19820221_20
hg3esa.pe19820222_06
hg3esa.pe19820222_16
hg3esa.pe19820223_02
hg3esa.pe19820223_12
hg3esa.pe19820223_22
hg3esa.pe19820224_08
hg3esa.pe19820224_18
hg3esa.pe19820225_04
hg3esa.pe19820225_14
hg3esa.pe19820226_00
hg3esa.pe19820226_10
hg3esa.pe19820226_20
hg3esa.pe19820227_06
hg3esa.pe19820227_16
hg3esa.pe19820228_02
hg3esa.pe19820228_12
hg3esa.pe19820228_22
hg3esa.pe19820229_08
hg3esa.pe19820229_18
hg3esa.pe19820230_04
hg3esa.pe19820230_14
hg3esa.pe19820301_00
hg3esa.pe19820301_10
hg3esa.pe19820301_20
hg3esa.pe19820302_06
hg3esa.pe19820302_16
hg3esa.pe19820303_02
hg3esa.pe19820303_12
hg3esa.pe19820303_22
hg3esa.pe19820304_08
hg3esa.pe19820304_18
hg3esa.pe19820305_04
hg3esa.pe19820305_14
hg3esa.pe19820306_00
hg3esa.pe19820306_10
hg3esa.pe19820306_20
hg3esa.pe19820307_06
hg3esa.pe19820307_16
hg3esa.pe19820308_02
hg3esa.pe19820308_12
hg3esa.pe19820308_22
hg3esa.pe19820309_08
hg3esa.pe19820309_18
hg3esa.pe19820310_04
hg3esa.pe19820310_14
hg3esa.pe19820311_00
hg3esa.pe19820311_10
hg3esa.pe19820311_20
hg3esa.pe19820312_06
hg3esa.pe19820312_16
hg3esa.pe19820313_02
hg3esa.pe19820313_12
hg3esa.pe19820313_22
hg3esa.pe19820314_08
hg3esa.pe19820314_18
hg3esa.pe19820315_04
hg3esa.pe19820315_14
hg3esa.pe19820316_00
hg3esa.pe19820316_10
hg3esa.pe19820316_20
hg3esa.pe19820317_06
hg3esa.pe19820317_16
hg3esa.pe19820318_02
hg3esa.pe19820318_12
hg3esa.pe19820318_22
hg3esa.pe19820319_08
hg3esa.pe19820319_18
hg3esa.pe19820320_04
hg3esa.pe19820320_14
hg3esa.pe19820321_00
hg3esa.pe19820321_10
hg3esa.pe19820321_20
hg3esa.pe19820322_06
hg3esa.pe19820322_16
hg3esa.pe19820323_02
hg3esa.pe19820323_12
hg3esa.pe19820323_22
hg3esa.pe19820324_08
hg3esa.pe19820324_18
hg3esa.pe19820325_04
hg3esa.pe19820325_14
hg3esa.pe19820326_00
hg3esa.pe19820326_10
hg3esa.pe19820326_20
hg3esa.pe19820327_06
hg3esa.pe19820327_16
hg3esa.pe19820328_02
hg3esa.pe19820328_12
hg3esa.pe19820328_22
hg3esa.pe19820329_08
hg3esa.pe19820329_18
hg3esa.pe19820330_04
hg3esa.pe19820401_00
hg3esa.pe19820401_10
hg3esa.pe19820401_20
hg3esa.pe19820402_06
hg3esa.pe19820402_16
hg3esa.pe19820403_02
hg3esa.pe19820403_12
hg3esa.pe19820403_22
hg3esa.pe19820404_08
hg3esa.pe19820404_18
hg3esa.pe19820405_04
hg3esa.pe19820405_14
hg3esa.pe19820406_00
hg3esa.pe19820406_10
hg3esa.pe19820406_20
hg3esa.pe19820407_06
hg3esa.pe19820407_16
hg3esa.pe19820408_02
hg3esa.pe19820408_12
hg3esa.pe19820408_22
hg3esa.pe19820409_08
hg3esa.pe19820409_18
hg3esa.pe19820410_04
hg3esa.pe19820410_14
hg3esa.pe19820411_00
hg3esa.pe19820411_10
hg3esa.pe19820411_20
hg3esa.pe19820412_06
hg3esa.pe19820412_16
hg3esa.pe19820413_02
hg3esa.pe19820413_12
hg3esa.pe19820413_22
hg3esa.pe19820414_08
hg3esa.pe19820414_18
hg3esa.pe19820415_04
hg3esa.pe19820415_14
hg3esa.pe19820416_00
hg3esa.pe19820416_10
hg3esa.pe19820416_20
hg3esa.pe19820417_06
hg3esa.pe19820417_16
hg3esa.pe19820418_02
hg3esa.pe19820418_12
hg3esa.pe19820418_22
hg3esa.pe19820419_08
hg3esa.pe19820419_18
hg3esa.pe19820420_04
hg3esa.pe19820420_14
hg3esa.pe19820421_00
hg3esa.pe19820421_10
hg3esa.pe19820421_20
hg3esa.pe19820422_06
hg3esa.pe19820422_16
hg3esa.pe19820423_02
hg3esa.pe19820423_12
hg3esa.pe19820423_22
hg3esa.pe19820424_08
hg3esa.pe19820424_18
hg3esa.pe19820425_04
hg3esa.pe19820425_14
hg3esa.pe19820426_00
hg3esa.pe19820426_10
hg3esa.pe19820426_20
hg3esa.pe19820427_06
hg3esa.pe19820427_16
hg3esa.pe19820428_02
hg3esa.pe19820428_12
hg3esa.pe19820428_22
hg3esa.pe19820429_08
hg3esa.pe19820429_18
hg3esa.pe19820430_04
hg3esa.pe19820501_00
hg3esa.pe19820501_10
hg3esa.pe19820501_20
hg3esa.pe19820502_06
hg3esa.pe19820502_16
hg3esa.pe19820503_02
hg3esa.pe19820503_12
hg3esa.pe19820503_22
hg3esa.pe19820504_08
hg3esa.pe19820504_18
hg3esa.pe19820505_04
hg3esa.pe19820505_14
hg3esa.pe19820506_00
hg3esa.pe19820506_10
hg3esa.pe19820506_20
hg3esa.pe19820507_06
hg3esa.pe19820507_16
hg3esa.pe19820508_02
hg3esa.pe19820508_12
hg3esa.pe19820508_22
hg3esa.pe19820509_08
hg3esa.pe19820509_18
hg3esa.pe19820510_04
hg3esa.pe19820510_14
hg3esa.pe19820511_00
hg3esa.pe19820511_10
hg3esa.pe19820511_20
hg3esa.pe19820512_06
hg3esa.pe19820512_16
hg3esa.pe19820513_02
hg3esa.pe19820513_12
hg3esa.pe19820513_22
hg3esa.pe19820514_08
hg3esa.pe19820514_18
hg3esa.pe19820515_04
hg3esa.pe19820515_14
hg3esa.pe19820516_00
hg3esa.pe19820516_10
hg3esa.pe19820516_20
hg3esa.pe19820517_06
hg3esa.pe19820517_16
hg3esa.pe19820518_02
hg3esa.pe19820518_12
hg3esa.pe19820518_22
hg3esa.pe19820519_08
hg3esa.pe19820519_18
hg3esa.pe19820520_04
hg3esa.pe19820520_14
hg3esa.pe19820521_00
hg3esa.pe19820521_10
hg3esa.pe19820521_20
hg3esa.pe19820522_06
hg3esa.pe19820522_16
hg3esa.pe19820523_02
hg3esa.pe19820523_12
hg3esa.pe19820523_22
hg3esa.pe19820524_08
hg3esa.pe19820524_18
hg3esa.pe19820525_04
hg3esa.pe19820525_14
hg3esa.pe19820526_00
hg3esa.pe19820526_10
hg3esa.pe19820526_20
hg3esa.pe19820527_06
hg3esa.pe19820527_16
hg3esa.pe19820528_02
hg3esa.pe19820528_12
hg3esa.pe19820528_22
hg3esa.pe19820529_08
hg3esa.pe19820529_18
hg3esa.pe19820530_04
hg3esa.pe19820601_00
hg3esa.pe19820601_10
hg3esa.pe19820601_20
hg3esa.pe19820602_06
hg3esa.pe19820602_16
hg3esa.pe19820603_02
hg3esa.pe19820603_12
hg3esa.pe19820603_22
hg3esa.pe19820604_08
hg3esa.pe19820604_18
hg3esa.pe19820605_04
hg3esa.pe19820605_14
hg3esa.pe19820606_00
hg3esa.pe19820606_10
hg3esa.pe19820606_20
hg3esa.pe19820607_06
hg3esa.pe19820607_16
hg3esa.pe19820608_02
hg3esa.pe19820608_12
hg3esa.pe19820608_22
hg3esa.pe19820609_08
hg3esa.pe19820609_18
hg3esa.pe19820610_04
hg3esa.pe19820610_14
hg3esa.pe19820611_00
hg3esa.pe19820611_10
hg3esa.pe19820611_20
hg3esa.pe19820612_06
hg3esa.pe19820612_16
hg3esa.pe19820613_02
hg3esa.pe19820613_12
hg3esa.pe19820613_22
hg3esa.pe19820614_08
hg3esa.pe19820614_18
hg3esa.pe19820615_04
hg3esa.pe19820615_14
hg3esa.pe19820616_00
hg3esa.pe19820616_10
hg3esa.pe19820616_20
hg3esa.pe19820617_06
hg3esa.pe19820617_16
hg3esa.pe19820618_02
hg3esa.pe19820618_12
hg3esa.pe19820618_22
hg3esa.pe19820619_08
hg3esa.pe19820619_18
hg3esa.pe19820620_04
hg3esa.pe19820620_14
hg3esa.pe19820621_00
hg3esa.pe19820621_10
hg3esa.pe19820621_20
hg3esa.pe19820622_06
hg3esa.pe19820622_16
hg3esa.pe19820623_02
hg3esa.pe19820623_12
hg3esa.pe19820623_22
hg3esa.pe19820624_08
hg3esa.pe19820624_18
hg3esa.pe19820625_04
hg3esa.pe19820625_14
hg3esa.pe19820626_00
hg3esa.pe19820626_10
hg3esa.pe19820626_20
hg3esa.pe19820627_06
hg3esa.pe19820627_16
hg3esa.pe19820628_02
hg3esa.pe19820628_12
hg3esa.pe19820628_22
hg3esa.pe19820629_08
hg3esa.pe19820629_18
hg3esa.pe19820630_04
hg3esa.pe19820701_00
hg3esa.pe19820701_10
hg3esa.pe19820701_20
hg3esa.pe19820702_06
hg3esa.pe19820702_16
hg3esa.pe19820703_02
hg3esa.pe19820703_12
hg3esa.pe19820703_22
hg3esa.pe19820704_08
hg3esa.pe19820704_18
hg3esa.pe19820705_04
hg3esa.pe19820705_14
hg3esa.pe19820706_00
hg3esa.pe19820706_10
hg3esa.pe19820706_20
hg3esa.pe19820707_06
hg3esa.pe19820707_16
hg3esa.pe19820708_02
hg3esa.pe19820708_12
hg3esa.pe19820708_22
hg3esa.pe19820709_08
hg3esa.pe19820709_18
hg3esa.pe19820710_04
hg3esa.pe19820710_14
hg3esa.pe19820711_00
hg3esa.pe19820711_10
hg3esa.pe19820711_20
hg3esa.pe19820712_06
hg3esa.pe19820712_16
hg3esa.pe19820713_02
hg3esa.pe19820713_12
hg3esa.pe19820713_22
hg3esa.pe19820714_08
hg3esa.pe19820714_18
hg3esa.pe19820715_04
hg3esa.pe19820715_14
hg3esa.pe19820716_00
hg3esa.pe19820716_10
hg3esa.pe19820716_20
hg3esa.pe19820717_06
hg3esa.pe19820717_16
hg3esa.pe19820718_02
hg3esa.pe19820718_12
hg3esa.pe19820718_22
hg3esa.pe19820719_08
hg3esa.pe19820719_18
hg3esa.pe19820720_04
hg3esa.pe19820720_14
hg3esa.pe19820721_00
hg3esa.pe19820721_10
hg3esa.pe19820721_20
hg3esa.pe19820722_06
hg3esa.pe19820722_16
hg3esa.pe19820723_02
hg3esa.pe19820723_12
hg3esa.pe19820723_22
hg3esa.pe19820724_08
hg3esa.pe19820724_18
hg3esa.pe19820725_04
hg3esa.pe19820725_14
hg3esa.pe19820726_00
hg3esa.pe19820726_10
hg3esa.pe19820726_20
hg3esa.pe19820727_06
hg3esa.pe19820727_16
hg3esa.pe19820728_02
hg3esa.pe19820728_12
hg3esa.pe19820728_22
hg3esa.pe19820729_08
hg3esa.pe19820729_18
hg3esa.pe19820730_04
hg3esa.pe19820801_00
hg3esa.pe19820801_10
hg3esa.pe19820801_20
hg3esa.pe19820802_06
hg3esa.pe19820802_16
hg3esa.pe19820803_02
hg3esa.pe19820803_12
hg3esa.pe19820803_22
hg3esa.pe19820804_08
hg3esa.pe19820804_18
hg3esa.pe19820805_04
hg3esa.pe19820805_14
hg3esa.pe19820806_00
hg3esa.pe19820806_10
hg3esa.pe19820806_20
hg3esa.pe19820807_06
hg3esa.pe19820807_16
hg3esa.pe19820808_02
hg3esa.pe19820808_12
hg3esa.pe19820808_22
hg3esa.pe19820809_08
hg3esa.pe19820809_18
hg3esa.pe19820810_04
hg3esa.pe19820810_14
hg3esa.pe19820811_00
hg3esa.pe19820811_10
hg3esa.pe19820811_20
hg3esa.pe19820812_06
hg3esa.pe19820812_16
hg3esa.pe19820813_02
hg3esa.pe19820813_12
hg3esa.pe19820813_22
hg3esa.pe19820814_08
hg3esa.pe19820814_18
hg3esa.pe19820815_04
hg3esa.pe19820815_14
hg3esa.pe19820816_00
hg3esa.pe19820816_10
hg3esa.pe19820816_20
hg3esa.pe19820817_06
hg3esa.pe19820817_16
hg3esa.pe19820818_02
hg3esa.pe19820818_12
hg3esa.pe19820818_22
hg3esa.pe19820819_08
hg3esa.pe19820819_18
hg3esa.pe19820820_04
hg3esa.pe19820820_14
hg3esa.pe19820821_00
hg3esa.pe19820821_10
hg3esa.pe19820821_20
hg3esa.pe19820822_06
hg3esa.pe19820822_16
hg3esa.pe19820823_02
hg3esa.pe19820823_12
hg3esa.pe19820823_22
hg3esa.pe19820824_08
hg3esa.pe19820824_18
hg3esa.pe19820825_04
hg3esa.pe19820825_14
hg3esa.pe19820826_00
hg3esa.pe19820826_10
hg3esa.pe19820826_20
hg3esa.pe19820827_06
hg3esa.pe19820827_16
hg3esa.pe19820828_02
hg3esa.pe19820828_12
hg3esa.pe19820828_22
hg3esa.pe19820829_08
hg3esa.pe19820829_18
hg3esa.pe19820830_04
hg3esa.pe19820901_00
hg3esa.pe19820901_10
hg3esa.pe19820901_20
hg3esa.pe19820902_06
hg3esa.pe19820902_16
hg3esa.pe19820903_02
hg3esa.pe19820903_12
hg3esa.pe19820903_22
hg3esa.pe19820904_08
hg3esa.pe19820904_18
hg3esa.pe19820905_04
hg3esa.pe19820905_14
hg3esa.pe19820906_00
hg3esa.pe19820906_10
hg3esa.pe19820906_20
hg3esa.pe19820907_06
hg3esa.pe19820907_16
hg3esa.pe19820908_02
hg3esa.pe19820908_12
hg3esa.pe19820908_22
hg3esa.pe19820909_08
hg3esa.pe19820909_18
hg3esa.pe19820910_04
hg3esa.pe19820910_14
hg3esa.pe19820911_00
hg3esa.pe19820911_10
hg3esa.pe19820911_20
hg3esa.pe19820912_06
hg3esa.pe19820912_16
hg3esa.pe19820913_02
hg3esa.pe19820913_12
hg3esa.pe19820913_22
hg3esa.pe19820914_08
hg3esa.pe19820914_18
hg3esa.pe19820915_04
hg3esa.pe19820915_14
hg3esa.pe19820916_00
hg3esa.pe19820916_10
hg3esa.pe19820916_20
hg3esa.pe19820917_06
hg3esa.pe19820917_16
hg3esa.pe19820918_02
hg3esa.pe19820918_12
hg3esa.pe19820918_22
hg3esa.pe19820919_08
hg3esa.pe19820919_18
hg3esa.pe19820920_04
hg3esa.pe19820920_14
hg3esa.pe19820921_00
hg3esa.pe19820921_10
hg3esa.pe19820921_20
hg3esa.pe19820922_06
hg3esa.pe19820922_16
hg3esa.pe19820923_02
hg3esa.pe19820923_12
hg3esa.pe19820923_22
hg3esa.pe19820924_08
hg3esa.pe19820924_18
hg3esa.pe19820925_04
hg3esa.pe19820925_14
hg3esa.pe19820926_00
hg3esa.pe19820926_10
hg3esa.pe19820926_20
hg3esa.pe19820927_06
hg3esa.pe19820927_16
hg3esa.pe19820928_02
hg3esa.pe19820928_12
hg3esa.pe19820928_22
hg3esa.pe19820929_08
hg3esa.pe19820929_18
hg3esa.pe19820930_04
hg3esa.pe19821001_00
hg3esa.pe19821001_10
hg3esa.pe19821001_20
hg3esa.pe19821002_06
hg3esa.pe19821002_16
hg3esa.pe19821003_02
hg3esa.pe19821003_12
hg3esa.pe19821003_22
hg3esa.pe19821004_08
hg3esa.pe19821004_18
hg3esa.pe19821005_04
hg3esa.pe19821005_14
hg3esa.pe19821006_00
hg3esa.pe19821006_10
hg3esa.pe19821006_20
hg3esa.pe19821007_06
hg3esa.pe19821007_16
hg3esa.pe19821008_02
hg3esa.pe19821008_12
hg3esa.pe19821008_22
hg3esa.pe19821009_08
hg3esa.pe19821009_18
hg3esa.pe19821010_04
hg3esa.pe19821010_14
hg3esa.pe19821011_00
hg3esa.pe19821011_10
hg3esa.pe19821011_20
hg3esa.pe19821012_06
hg3esa.pe19821012_16
hg3esa.pe19821013_02
hg3esa.pe19821013_12
hg3esa.pe19821013_22
hg3esa.pe19821014_08
hg3esa.pe19821014_18
hg3esa.pe19821015_04
hg3esa.pe19821015_14
hg3esa.pe19821016_00
hg3esa.pe19821016_10
hg3esa.pe19821016_20
hg3esa.pe19821017_06
hg3esa.pe19821017_16
hg3esa.pe19821018_02
hg3esa.pe19821018_12
hg3esa.pe19821018_22
hg3esa.pe19821019_08
hg3esa.pe19821019_18
hg3esa.pe19821020_04
hg3esa.pe19821020_14
hg3esa.pe19821021_00
hg3esa.pe19821021_10
hg3esa.pe19821021_20
hg3esa.pe19821022_06
hg3esa.pe19821022_16
hg3esa.pe19821023_02
hg3esa.pe19821023_12
hg3esa.pe19821023_22
hg3esa.pe19821024_08
hg3esa.pe19821024_18
hg3esa.pe19821025_04
hg3esa.pe19821025_14
hg3esa.pe19821026_00
hg3esa.pe19821026_10
hg3esa.pe19821026_20
hg3esa.pe19821027_06
hg3esa.pe19821027_16
hg3esa.pe19821028_02
hg3esa.pe19821028_12
hg3esa.pe19821028_22
hg3esa.pe19821029_08
hg3esa.pe19821029_18
hg3esa.pe19821030_04

hg3esa.pe19821101_00
hg3esa.pe19821101_10
hg3esa.pe19821101_20
hg3esa.pe19821102_06
hg3esa.pe19821102_16
hg3esa.pe19821103_02
hg3esa.pe19821103_12
hg3esa.pe19821103_22
hg3esa.pe19821104_08
hg3esa.pe19821104_18
hg3esa.pe19821105_04
hg3esa.pe19821105_14
hg3esa.pe19821106_00
hg3esa.pe19821106_10
hg3esa.pe19821106_20
hg3esa.pe19821107_06
hg3esa.pe19821107_16
hg3esa.pe19821108_02
hg3esa.pe19821108_12
hg3esa.pe19821108_22
hg3esa.pe19821109_08
hg3esa.pe19821109_18
hg3esa.pe19821110_04
hg3esa.pe19821110_14
hg3esa.pe19821111_00
hg3esa.pe19821111_10
hg3esa.pe19821111_20
hg3esa.pe19821112_06
hg3esa.pe19821112_16
hg3esa.pe19821113_02
hg3esa.pe19821113_12
hg3esa.pe19821113_22
hg3esa.pe19821114_08
hg3esa.pe19821114_18
hg3esa.pe19821115_04
hg3esa.pe19821115_14
hg3esa.pe19821116_00
hg3esa.pe19821116_10
hg3esa.pe19821116_20
hg3esa.pe19821117_06
hg3esa.pe19821117_16
hg3esa.pe19821118_02
hg3esa.pe19821118_12
hg3esa.pe19821118_22
hg3esa.pe19821119_08
hg3esa.pe19821119_18
hg3esa.pe19821120_04
hg3esa.pe19821120_14
hg3esa.pe19821121_00
hg3esa.pe19821121_10
hg3esa.pe19821121_20
hg3esa.pe19821122_06
hg3esa.pe19821122_16
hg3esa.pe19821123_02
hg3esa.pe19821123_12
hg3esa.pe19821123_22
hg3esa.pe19821124_08
hg3esa.pe19821124_18
hg3esa.pe19821125_04
hg3esa.pe19821125_14
hg3esa.pe19821126_00
hg3esa.pe19821126_10
hg3esa.pe19821126_20
hg3esa.pe19821127_06
hg3esa.pe19821127_16
hg3esa.pe19821128_02
hg3esa.pe19821128_12
hg3esa.pe19821128_22
hg3esa.pe19821129_08
hg3esa.pe19821129_18
hg3esa.pe19821130_04

hg3esa.pe19821201_00
hg3esa.pe19821201_10
hg3esa.pe19821201_20
hg3esa.pe19821202_06
hg3esa.pe19821202_16
hg3esa.pe19821203_02
hg3esa.pe19821203_12
hg3esa.pe19821203_22
hg3esa.pe19821204_08
hg3esa.pe19821204_18
hg3esa.pe19821205_04
hg3esa.pe19821205_14
hg3esa.pe19821206_00
hg3esa.pe19821206_10
hg3esa.pe19821206_20
hg3esa.pe19821207_06
hg3esa.pe19821207_16
hg3esa.pe19821208_02
hg3esa.pe19821208_12
hg3esa.pe19821208_22
hg3esa.pe19821209_08
hg3esa.pe19821209_18
hg3esa.pe19821210_04
hg3esa.pe19821210_14
hg3esa.pe19821211_00
hg3esa.pe19821211_10
hg3esa.pe19821211_20
hg3esa.pe19821212_06
hg3esa.pe19821212_16
hg3esa.pe19821213_02
hg3esa.pe19821213_12
hg3esa.pe19821213_22
hg3esa.pe19821214_08
hg3esa.pe19821214_18
hg3esa.pe19821215_04
hg3esa.pe19821215_14
hg3esa.pe19821216_00
hg3esa.pe19821216_10
hg3esa.pe19821216_20
hg3esa.pe19821217_06
hg3esa.pe19821217_16
hg3esa.pe19821218_02
hg3esa.pe19821218_12
hg3esa.pe19821218_22
hg3esa.pe19821219_08
hg3esa.pe19821219_18
hg3esa.pe19821220_04
hg3esa.pe19821220_14
hg3esa.pe19821221_00
hg3esa.pe19821221_10
hg3esa.pe19821221_20
hg3esa.pe19821222_06
hg3esa.pe19821222_16
hg3esa.pe19821223_02
hg3esa.pe19821223_12
hg3esa.pe19821223_22
hg3esa.pe19821224_08
hg3esa.pe19821224_18
hg3esa.pe19821225_04
hg3esa.pe19821225_14
hg3esa.pe19821226_00
hg3esa.pe19821226_10
hg3esa.pe19821226_20
hg3esa.pe19821227_06
hg3esa.pe19821227_16
hg3esa.pe19821228_02
hg3esa.pe19821228_12
hg3esa.pe19821228_22
hg3esa.pe19821229_08
hg3esa.pe19821229_18
hg3esa.pe19821230_04

hg3esa.pe19830101_00
hg3esa.pe19830101_10
hg3esa.pe19830101_20
hg3esa.pe19830102_06
hg3esa.pe19830102_16
hg3esa.pe19830103_02
hg3esa.pe19830103_12
hg3esa.pe19830103_22
hg3esa.pe19830104_08
hg3esa.pe19830104_18
hg3esa.pe19830105_04
hg3esa.pe19830105_14
hg3esa.pe19830106_00
hg3esa.pe19830106_10
hg3esa.pe19830106_20
hg3esa.pe19830107_06
hg3esa.pe19830107_16
hg3esa.pe19830108_02
hg3esa.pe19830108_12
hg3esa.pe19830108_22
hg3esa.pe19830109_08
hg3esa.pe19830109_18
hg3esa.pe19830110_04
hg3esa.pe19830110_14
hg3esa.pe19830111_00
hg3esa.pe19830111_10
hg3esa.pe19830111_20
hg3esa.pe19830112_06
hg3esa.pe19830112_16
hg3esa.pe19830113_02
hg3esa.pe19830113_12
hg3esa.pe19830113_22
hg3esa.pe19830114_08
hg3esa.pe19830114_18
hg3esa.pe19830115_04
hg3esa.pe19830115_14
hg3esa.pe19830116_00
hg3esa.pe19830116_10
hg3esa.pe19830116_20
hg3esa.pe19830117_06
hg3esa.pe19830117_16
hg3esa.pe19830118_02
hg3esa.pe19830118_12
hg3esa.pe19830118_22
hg3esa.pe19830119_08
hg3esa.pe19830119_18
hg3esa.pe19830120_04
hg3esa.pe19830120_14
hg3esa.pe19830121_00
hg3esa.pe19830121_10
hg3esa.pe19830121_20
hg3esa.pe19830122_06
hg3esa.pe19830122_16
hg3esa.pe19830123_02
hg3esa.pe19830123_12
hg3esa.pe19830123_22
hg3esa.pe19830124_08
hg3esa.pe19830124_18
hg3esa.pe19830125_04
hg3esa.pe19830125_14
hg3esa.pe19830126_00
hg3esa.pe19830126_10
hg3esa.pe19830126_20
hg3esa.pe19830127_06
hg3esa.pe19830127_16
hg3esa.pe19830128_02
hg3esa.pe19830128_12
hg3esa.pe19830128_22
hg3esa.pe19830129_08
hg3esa.pe19830129_18
hg3esa.pe19830130_04
hg3esa.pe19830130_14
"

aph="
hg3esa.ph19811001
hg3esa.ph19811011
hg3esa.ph19811021
hg3esa.ph19811101
hg3esa.ph19811111
hg3esa.ph19811121
hg3esa.ph19811201
hg3esa.ph19811211
hg3esa.ph19811221
hg3esa.ph19820101
hg3esa.ph19820111
hg3esa.ph19820121
hg3esa.ph19820201
hg3esa.ph19820211
hg3esa.ph19820221
hg3esa.ph19820301
hg3esa.ph19820311
hg3esa.ph19820321
hg3esa.ph19820401
hg3esa.ph19820411
hg3esa.ph19820421
hg3esa.ph19820501
hg3esa.ph19820511
hg3esa.ph19820521
hg3esa.ph19820601
hg3esa.ph19820611
hg3esa.ph19820621
hg3esa.ph19820701
hg3esa.ph19820711
hg3esa.ph19820721
hg3esa.ph19820801
hg3esa.ph19820811
hg3esa.ph19820821
hg3esa.ph19820901
hg3esa.ph19820911
hg3esa.ph19820921
hg3esa.ph19821001
hg3esa.ph19821011
hg3esa.ph19821021
hg3esa.ph19821101
hg3esa.ph19821111
hg3esa.ph19821121
hg3esa.ph19821201
hg3esa.ph19821211
hg3esa.ph19821221
hg3esa.ph19830101
hg3esa.ph19830111
hg3esa.ph19830121"

apj="
hg3esa.pj19820101.pp
hg3esa.pj19820401.pp
hg3esa.pj19820701.pp
hg3esa.pj19821001.pp
hg3esa.pj19830101.pp"

afinal="
hg3esa.da19830201_00
hg3esa.pe19830130_14
hg3esa.ph19830121
hg3esa.pj19830101"

ipd="
cice_hg3esi_10d_19811001-19811011.nc
cice_hg3esi_10d_19811011-19811021.nc
cice_hg3esi_10d_19811021-19811101.nc
cice_hg3esi_10d_19811101-19811111.nc
cice_hg3esi_10d_19811111-19811121.nc
cice_hg3esi_10d_19811121-19811201.nc
cice_hg3esi_10d_19811201-19811211.nc
cice_hg3esi_10d_19811211-19811221.nc
cice_hg3esi_10d_19811221-19820101.nc
cice_hg3esi_10d_19820101-19820111.nc
cice_hg3esi_10d_19820111-19820121.nc
cice_hg3esi_10d_19820121-19820201.nc
cice_hg3esi_10d_19820201-19820211.nc
cice_hg3esi_10d_19820211-19820221.nc
cice_hg3esi_10d_19820221-19820301.nc
cice_hg3esi_10d_19820301-19820311.nc
cice_hg3esi_10d_19820311-19820321.nc
cice_hg3esi_10d_19820321-19820401.nc
cice_hg3esi_10d_19820401-19820411.nc
cice_hg3esi_10d_19820411-19820421.nc
cice_hg3esi_10d_19820421-19820501.nc
cice_hg3esi_10d_19820501-19820511.nc
cice_hg3esi_10d_19820511-19820521.nc
cice_hg3esi_10d_19820521-19820601.nc
cice_hg3esi_10d_19820601-19820611.nc
cice_hg3esi_10d_19820611-19820621.nc
cice_hg3esi_10d_19820621-19820701.nc
cice_hg3esi_10d_19820701-19820711.nc
cice_hg3esi_10d_19820711-19820721.nc
cice_hg3esi_10d_19820721-19820801.nc
cice_hg3esi_10d_19820801-19820811.nc
cice_hg3esi_10d_19820811-19820821.nc
cice_hg3esi_10d_19820821-19820901.nc
cice_hg3esi_10d_19820901-19820911.nc
cice_hg3esi_10d_19820911-19820921.nc
cice_hg3esi_10d_19820921-19821001.nc
cice_hg3esi_10d_19821001-19821011.nc
cice_hg3esi_10d_19821011-19821021.nc
cice_hg3esi_10d_19821021-19821101.nc
cice_hg3esi_10d_19821101-19821111.nc
cice_hg3esi_10d_19821111-19821121.nc
cice_hg3esi_10d_19821121-19821201.nc
"

ipm="
cice_hg3esi_1m_19811001-19811101.nc
cice_hg3esi_1m_19811101-19811201.nc
cice_hg3esi_1m_19811201-19820101.nc
cice_hg3esi_1m_19820101-19820201.nc
cice_hg3esi_1m_19820201-19820301.nc
cice_hg3esi_1m_19820301-19820401.nc
cice_hg3esi_1m_19820401-19820501.nc
cice_hg3esi_1m_19820501-19820601.nc
cice_hg3esi_1m_19820601-19820701.nc
cice_hg3esi_1m_19820701-19820801.nc
cice_hg3esi_1m_19820801-19820901.nc
cice_hg3esi_1m_19820901-19821001.nc
cice_hg3esi_1m_19821001-19821101.nc
cice_hg3esi_1m_19821101-19821201.nc
cice_hg3esi_1m_19821201-19830101.nc
cice_hg3esi_1m_19830101-19830201.nc"

# ips="  <-- Files produced when mean ref time is Dec 1st
# cice_hg3esi_1s_19811201-19820301.nc
# cice_hg3esi_1s_19820301-19820601.nc
# cice_hg3esi_1s_19820601-19820901.nc
# cice_hg3esi_1s_19820901-19821201.nc"
ips="
cice_hg3esi_1s_19811001-19820101.nc
cice_hg3esi_1s_19820101-19820401.nc
cice_hg3esi_1s_19820401-19820701.nc
cice_hg3esi_1s_19820701-19821001.nc"

# ipy="cice_hg3esi_1y_19811201-19821201.nc"  <-- Files produced when mean ref time is Dec 1st
ipy="cice_hg3esi_1y_19820101-19830101.nc"

idumps="
hg3esi.restart.1981-12-01-00000
hg3esi.restart.1982-06-01-00000
hg3esi.restart.1982-12-01-00000
hg3esi.restart.1983-02-01-00000"

# ifinal="  <-- Files produced when mean ref time is Dec 1st
# cice_hg3esi_1m_19821201-19830101.nc
# cice_hg3esi_1m_19830101-19830201.nc
# hg3esi.restart.1983-02-01-00000"
ifinal="
cice_hg3esi_1m_19830101-19830201.nc
hg3esi.restart.1983-02-01-00000"

opd=""

# opm="  <-- Files produced when mean monthly mean production is active
# nemo_hg3eso_1m_19811001-19811101_grid-V.nc
# nemo_hg3eso_1m_19811101-19811201_grid-V.nc
# nemo_hg3eso_1m_19811201-19820101_grid-V.nc
# nemo_hg3eso_1m_19820101-19820201_grid-V.nc
# nemo_hg3eso_1m_19820201-19820301_grid-V.nc
# nemo_hg3eso_1m_19820301-19820401_grid-V.nc
# nemo_hg3eso_1m_19820401-19820501_grid-V.nc
# nemo_hg3eso_1m_19820501-19820601_grid-V.nc
# nemo_hg3eso_1m_19820601-19820701_grid-V.nc
# nemo_hg3eso_1m_19820701-19820801_grid-V.nc
# nemo_hg3eso_1m_19820801-19820901_grid-V.nc
# nemo_hg3eso_1m_19820901-19821001_grid-V.nc
# nemo_hg3eso_1m_19821001-19821101_grid-V.nc
# nemo_hg3eso_1m_19821101-19821201_grid-V.nc
# nemo_hg3eso_1m_19821201-19830101_grid-V.nc
# nemo_hg3eso_1m_19830101-19830201_grid-V.nc"

# ops="  <-- Files produced when mean ref time is Dec 1st
# nemo_hg3eso_1s_19811201-19820301_grid-V.nc 
# nemo_hg3eso_1s_19820301-19820601_grid-V.nc
# nemo_hg3eso_1s_19820601-19820901_grid-V.nc
# nemo_hg3eso_1s_19820901-19821201_grid-V.nc"

ops="
nemo_hg3eso_1s_19811001-19820101_grid-V.nc 
nemo_hg3eso_1s_19820101-19820401_grid-V.nc
nemo_hg3eso_1s_19820401-19820701_grid-V.nc
nemo_hg3eso_1s_19820701-19821001_grid-V.nc"

# opy="  <-- Files produced when mean ref time is Dec 1st
# nemo_hg3eso_1s_19811201-19820301_grid-V.nc 
# nemo_hg3eso_1s_19820301-19820601_grid-V.nc
# nemo_hg3eso_1s_19820601-19820901_grid-V.nc
# nemo_hg3eso_1s_19820901-19821201_grid-V.nc
# nemo_hg3eso_1y_19811201-19821201_grid-V.nc"

# opy="  <-- Files produced when mean annual mean production is active (mean ref: Jan 1st)
# nemo_hg3eso_1y_19820101-19830101_grid-V.nc"

odumps="
hg3eso_19811130_restart.nc
hg3eso_19820530_restart.nc
hg3eso_19821130_restart.nc
hg3eso_19830130_restart.nc"

# ofinal="  <-- Files produced when mean ref time is Dec 1st
# nemo_hg3eso_1m_19821201-19830101_grid-V.nc
# nemo_hg3eso_1m_19830101-19830201_grid-V.nc
# hg3eso_19830130_restart.nc
# hg3eso_19830130_restart_0000.nc
# hg3eso_19830130_restart_0001.nc
# hg3eso_19830130_restart_0002.nc"

# nemo_hg3eso_1m_19830101-19830201_grid-V.nc  <-- addition to ofinal when monthly mean production is active
ofinal="
hg3eso_19830130_restart.nc
hg3eso_19830130_restart_0000.nc
hg3eso_19830130_restart_0001.nc
hg3eso_19830130_restart_0002.nc"

CYLC_SUITE_LOG_DIR=${CYLC_SUITE_LOG_DIR:-$HOME/cylc-run/test_postproc/log/suite}
logfile=job/1/postproc_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/[0-9][0-9]/job-arch*.log
search=$(grep -r ARCHIVE $CYLC_SUITE_LOG_DIR/../$logfile)
fails=$(grep -r FAILED $CYLC_SUITE_LOG_DIR/../$logfile)
ghost=$(grep -r "does not exist" $CYLC_SUITE_LOG_DIR/../$logfile)

RC=0

echo "[INFO] Checking Atmosphere output all present and correct..."
for fn in $adumps $ape $aph $apj $apm $apm $aps $apy; do
    if [[ "$search" != *"$fn WOULD BE ARCHIVED"* ]] && \
        [[ "$search" != *"$fn ARCHIVE OK"* ]] && \
	[[ "$search" != *"$fn FILE NOT ARCHIVED. File contains no fields"* ]] && \
	[[ "$search" != *"$fn FILE NOT ARCHIVED. Empty file"* ]]; then 
        echo "[FAIL] File archive not logged: $fn"
        RC=$((RC + 1))
    fi
    if [[ "$fails" == *"$fn ARCHIVE FAILED"* ]]; then 
        echo "[FAIL] File archive failed: $fn"
        RC=$((RC + 11))
    fi
    if [[ "$ghost" == *"$fn FILE NOT ARCHIVED"* ]]; then 
        echo "[FAIL] File not archived - does not exist: $fn"
        RC=$((RC + 111))
    fi
done

atmosdisk=$(ls $CYLC_SUITE_SHARE_DIR/data/postproc/ATMOSdata)
for fn in $afinal; do
    match=false
    for ondisk in $atmosdisk; do
	if [[ "$ondisk" == "$fn" ]]; then
	    match=true
	    break
	fi
    done
    if ! $match; then
	echo "[FAIL] File not on disk: $fn"
        RC=$((RC + 1111))
    fi
done

echo
echo "[INFO] Checking NEMO output all present and correct..."
for fn in $odumps $opd $opm $ops $opy; do
    if [[ "$search" != *"$fn WOULD BE ARCHIVED"* ]] && [[ "$search" != *"$fn ARCHIVE OK"* ]]; then 
        echo "[FAIL] File archive not logged: $fn"
        RC=$((RC + 2))
    fi
    if [[ "$fails" == *"$fn ARCHIVE FAILED"* ]]; then 
        echo "[FAIL] File archive failed: $fn"
        RC=$((RC + 22))
    fi
    if [[ "$ghost" == *"$fn FILE NOT ARCHIVED"* ]]; then 
        echo "[FAIL] File not archived - does not exist: $fn"
        RC=$((RC + 222))
    fi
done

nemodisk=$(ls $CYLC_SUITE_SHARE_DIR/data/postproc/NEMOdata)
for fn in $ofinal; do
    match=false
    for ondisk in $nemodisk; do
	if [[ "$ondisk" == "$fn" ]]; then
	    match=true
	    break
	fi
    done
    if ! $match; then
	echo "[FAIL] File not on disk: $fn"
	RC=$((RC + 2222))
    fi
done

echo
echo "[INFO] Checking CICE output all present and correct..."
for fn in $idumps $ipd $ipm $ips $ipy; do
    if [[ "$search" != *"$fn WOULD BE ARCHIVED"* ]] && [[ "$search" != *"$fn ARCHIVE OK"* ]]; then 
        echo "[FAIL] File archive not logged: $fn"
        RC=$((RC + 3))
    fi
    if [[ "$fails" == *"$fn ARCHIVE FAILED"* ]]; then 
        echo "[FAIL] File archive failed: $fn"
        RC=$((RC + 33))
    fi
    if [[ "$ghost" == *"$fn FILE NOT ARCHIVED"* ]]; then 
        echo "[FAIL] File not archived - does not exist: $fn"
        RC=$((RC + 333))
    fi
done

cicedisk=$(ls $CYLC_SUITE_SHARE_DIR/data/postproc/CICEdata)
for fn in $ifinal; do
    match=false
    for ondisk in $cicedisk; do
	if [[ "$ondisk" == "$fn" ]]; then
	    match=true
	    break
	fi
    done
    if ! $match; then
	echo "[FAIL] File not on disk: $fn"
	RC=$((RC + 3333))
    fi  
done

exit $RC
