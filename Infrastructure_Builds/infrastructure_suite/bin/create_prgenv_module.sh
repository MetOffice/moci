#!/usr/bin/env bash
#
# NAME: create_prgenv_module.sh
#
# DESCRIPTION: Writes the GC Programming Environment module, containing the
#              relative paths to the OASIS3-MCT and XIOS modules
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    PRG_ENV_NAME
#    PRG_ENV_VERSION
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

module_file_path=$MODULE_BASE/modules/$PRG_ENV_NAME/$PRG_ENV_VERSION
mkdir -p $module_file_path
module_file=$module_file_path/$revision

rm -r $module_file
cat <<EOF >>$module_file
#%Module1.0
proc ModulesHelp { } {
EOF
if [ "$XIOS_ONLY" = "True" ]; then
    cat <<EOF >>$module_file
    puts stderr "Sets up the programming environment for XIOS
EOF
else
    cat <<EOF >>$module_file
    puts stderr "Sets up the programming environment for XIOS and Oasis3-mct
EOF
fi
cat <<EOF >>$module_file
Build by Rose suite:
Suite URL: $SUITE_URL
Suite Revision Number: $SUITE_REVISION
"
}
EOF
if [ "$XIOS_ONLY" = "True" ]; then
    cat <<EOF >>$module_file
module-whatis The XIOS I/O server for use with weather/climate models
EOF
else
    cat <<EOF >>$module_file
module-whatis The XIOS I/O server and Oasis3-MCT coupler for use with weather/clmiate models
EOF
fi
cat <<EOF >>$module_file

conflict GC3-PrgEnv

set version $PRG_ENV_VERSION

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
if [ "XIOS_ONLY" = "True" ]; then
    line="module load $XIOS_MODULE_PATH";
    cat <<EOF >>$module_file
$line
EOF
else
    for mod in $OASIS_MODULE_PATH $XIOS_MODULE_PATH; do
	line="module load $mod"
	cat <<EOF >>$module_file
$line
EOF
    done
fi

# create a script to allow the PrgEnv module to be used by subsequent tasks
rm $CYLC_SUITE_RUN_DIR/share/load_prgenv_mod.sh
cat <<EOF > $CYLC_SUITE_RUN_DIR/share/load_prgenv_mod.sh
export TEST_PRGENV_MODULE_PATH=$MODULE_BASE/modules
export TEST_PRGENV_MODULE_NAME=$PRG_ENV_NAME/$PRG_ENV_VERSION/$revision
EOF

#End of script test
ls $module_file_path
[ $? -eq 0 ] || exit 1
