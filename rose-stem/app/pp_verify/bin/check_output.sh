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
#
###############################################################################

adumps="
hg3esa.da19811101_00
hg3esa.da19811201_00
hg3esa.da19820101_00
hg3esa.da19820201_00
hg3esa.da19820301_00
hg3esa.da19820401_00
hg3esa.da19820501_00
hg3esa.da19820601_00
hg3esa.da19820701_00
hg3esa.da19820801_00
hg3esa.da19820901_00
hg3esa.da19821001_00
hg3esa.da19821101_00
hg3esa.da19821201_00
hg3esa.da19830101_00"

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
hg3esa.ps1981son.pp
hg3esa.ps1982djf.pp
hg3esa.ps1982mam.pp
hg3esa.ps1982jja.pp
hg3esa.ps1982son.pp"

apy="hg3esa.py19821201.pp"

aph="
hg3esa.ph19811001.pp
hg3esa.ph19811011.pp
hg3esa.ph19811021.pp
hg3esa.ph19811101.pp
hg3esa.ph19811111.pp
hg3esa.ph19811121.pp
hg3esa.ph19811201.pp
hg3esa.ph19811211.pp
hg3esa.ph19811221.pp
hg3esa.ph19820101.pp
hg3esa.ph19820111.pp
hg3esa.ph19820121.pp
hg3esa.ph19820201.pp
hg3esa.ph19820211.pp
hg3esa.ph19820221.pp
hg3esa.ph19820301.pp
hg3esa.ph19820311.pp
hg3esa.ph19820321.pp
hg3esa.ph19820401.pp
hg3esa.ph19820411.pp
hg3esa.ph19820421.pp
hg3esa.ph19820501.pp
hg3esa.ph19820511.pp
hg3esa.ph19820521.pp
hg3esa.ph19820601.pp
hg3esa.ph19820611.pp
hg3esa.ph19820621.pp
hg3esa.ph19820701.pp
hg3esa.ph19820711.pp
hg3esa.ph19820721.pp
hg3esa.ph19820801.pp
hg3esa.ph19820811.pp
hg3esa.ph19820821.pp
hg3esa.ph19820901.pp
hg3esa.ph19820911.pp
hg3esa.ph19820921.pp
hg3esa.ph19821001.pp
hg3esa.ph19821011.pp
hg3esa.ph19821021.pp
hg3esa.ph19821101.pp
hg3esa.ph19821111.pp
hg3esa.ph19821121.pp
hg3esa.ph19821201.pp
hg3esa.ph19821211.pp"

apj="
a.pj19811201
a.pj19820301
a.pj19820601
a.pj19820901"

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
cice_hg3esi_1m_19821001-19821101.nc"

ips="
cice_hg3esi_1s_19811201-19820301.nc
cice_hg3esi_1s_19820301-19820601.nc
cice_hg3esi_1s_19820601-19820901.nc
cice_hg3esi_1s_19820901-19821201.nc"

ipy="cice_hg3esi_1y_19811201-19821201.nc"

idumps="
hg3esi.restart.1981-12-01-00000
hg3esi.restart.1982-06-01-00000
hg3esi.restart.1982-12-01-00000"

opd=""

opm="
nemo_hg3eso_1m_19811001-19811101_grid-V.nc
nemo_hg3eso_1m_19811101-19811201_grid-V.nc
nemo_hg3eso_1m_19811201-19820101_grid-V.nc
nemo_hg3eso_1m_19820101-19820201_grid-V.nc
nemo_hg3eso_1m_19820201-19820301_grid-V.nc
nemo_hg3eso_1m_19820301-19820401_grid-V.nc
nemo_hg3eso_1m_19820401-19820501_grid-V.nc
nemo_hg3eso_1m_19820501-19820601_grid-V.nc
nemo_hg3eso_1m_19820601-19820701_grid-V.nc
nemo_hg3eso_1m_19820701-19820801_grid-V.nc
nemo_hg3eso_1m_19820801-19820901_grid-V.nc
nemo_hg3eso_1m_19820901-19821001_grid-V.nc
nemo_hg3eso_1m_19821001-19821101_grid-V.nc
nemo_hg3eso_1m_19821101-19821201_grid-V.nc"

#1st seasonal mean removed since MOCI #62 - start date moved to October
#hg3eso_1s_19810901_19811130_grid_V.nc
ops="
nemo_hg3eso_1s_19811201-19820301_grid-V.nc 
nemo_hg3eso_1s_19820301-19820601_grid-V.nc
nemo_hg3eso_1s_19820601-19820901_grid-V.nc
nemo_hg3eso_1s_19820901-19821201_grid-V.nc"

opy="
nemo_hg3eso_1y_19811201-19821201_grid-V.nc"

odumps="
hg3eso_19811130_restart.nc
hg3eso_19820530_restart.nc
hg3eso_19821130_restart.nc"

CYLC_SUITE_LOG_DIR=${CYLC_SUITE_LOG_DIR:-$HOME/cylc-run/test_postproc/log/suite}
logfile=job/1/postproc_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/[0-9][0-9]/job-arch*.log
search=$(grep -r ARCHIVE $CYLC_SUITE_LOG_DIR/../$logfile)
fails=$(grep -r FAILED $CYLC_SUITE_LOG_DIR/../$logfile)
ghost=$(grep -r "does not exist" $CYLC_SUITE_LOG_DIR/../$logfile)

RC=0

echo "[INFO] Checking Atmosphere output all present and correct..."
for fn in $adumps $aph $apj $apm $apm $aps $apy; do
    if [[ "$search" != *"$fn WOULD BE ARCHIVED"* ]] && [[ "$search" != *"$fn ARCHIVE OK"* ]] && \
	[[ "$search" != *"$fn FILE NOT ARCHIVED. File contains no fields"* ]]; then 
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

exit $RC
