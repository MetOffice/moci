#!/usr/bin/env bash
#
# NAME: create_prgenv_module.sh
#
# DESCRIPTION: Writes the GC Programming Environment module, containing the
#              relative paths to the OASIS3-MCT and XIOS modules
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    GC_PRG_ENV_NAME
#    GC_PRG_ENV_VERSION
#    MODULE_STR
# 
# ENVIRONMENT VARIABLES (OPTIONAL):
#    MODULE_BASE
#    SUITE_REVISION
#    SUITE_URL
# 

if [ -z $MODULE_BASE ]; then
    MODULE_BASE=$CYLC_SUITE_RUN_DIR/share/modules
fi
mkdir $MODULE_BASE

if [ -z "$SUITE_URL" ]; then
    SUITE_URL='URL: undefined'
fi
if [ -z "$SUITE_REVISION" ]; then
    SUITE_REVISION='Revision: undefined'
    revision='undefined'
else
    revision=$(echo $SUITE_REVISION | grep -oP '\d+')
fi

module_file_path=$MODULE_BASE/modules/$GC_PRG_ENV_NAME/$GC_PRG_ENV_VERSION
mkdir -p $module_file_path
module_file=$module_file_path/$revision

rm -r $module_file
cat <<EOF >$module_file
#%Module1.0
proc ModulesHelp { } {
    puts stderr "Sets up the programming environment for XIOS and Oasis3-mct
Build by Rose suite:
Suite URL: $SUITE_URL
Suite Revision Number: $SUITE_REVISION
"
}

module-whatis The XIOS I/O server for use with weather/climate models 

conflict GC3-PrgEnv

set version $GC_PRG_ENV_VERSION

EOF

for mod in $MODULE_STR; do
    if [[ $mod == *'PrgEnv'* ]]; then
	line="module swap PrgEnv-cray $mod"
    else
	line="module load $mod"
    fi
    cat <<EOF >>$module_file
$line
EOF
done
# now do the oasis and xios modules
for mod in $OASIS_MODULE_PATH $XIOS_MODULE_PATH; do
    line="module load $mod"
    cat <<EOF >>$module_file
$line
EOF
done
