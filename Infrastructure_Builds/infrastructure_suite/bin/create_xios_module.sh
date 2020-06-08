#!/usr/bin/env bash
#
# NAME: create_xios_module.sh
#
# DESCRIPTION: Writes the XIOS environment module file, and organises the
#              module package directory
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    XIOS_MOD_NAME
#    XIOS_MOD_VERSION
#    XIOS_PATH
#    XIOS_REV
#    XIOS_URL
#    XIOS_VERSION
# 
# ENVIRONMENT VARIABLES (OPTIONAL):
#     MODULE_BASE
#     SUITE_REVISION
#     SUITE_URL
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

xios_mod_version_path=$XIOS_MOD_NAME/$XIOS_MOD_VERSION/$revision
xios_dir=$MODULE_BASE/packages/$xios_mod_version_path/$XIOS_REV
mkdir -p $xios_dir
xios_mod_dir=$MODULE_BASE/modules/$xios_mod_version_path
mkdir -p $xios_mod_dir

# copy our builds into the module package directory
cp -r $XIOSPATH/bin $xios_dir
cp -r $XIOSPATH/inc $xios_dir
cp -r $XIOSPATH/inputs $xios_dir
cp -r $XIOSPATH/lib $xios_dir

rm $MODULE_BASE/modules/$xios_mod_version_path/$XIOS_REV
cat <<EOF >$MODULE_BASE/modules/$xios_mod_version_path/$XIOS_REV
#%Module1.0
proc ModulesHelp { } {
    puts stderr "Sets up Oasis3-MCT coupler I/O server for use
Source URL: $XIOS_URL/$XIOS_VERSION
Revision: $XIOS_REV
Built using Rose suite:
$SUITE_URL
$SUITE_REVISION
"
}

module-whatis The XIOS I/O server for use with weather/climate models

conflict XIOS

set version $XIOS_MOD_VERSION
set module_base $MODULE_BASE
set xios_dir $xios_dir

EOF
# add our prerequesits to the same file
for prereq in $MODULE_STR; do
    cat <<EOF >>$MODULE_BASE/modules/$xios_mod_version_path/$XIOS_REV
prereq $prereq
EOF
done;
cat <<EOF >>$MODULE_BASE/modules/$xios_mod_version_path/$XIOS_REV
setenv XIOS_PATH $xios_dir
setenv xios_path $xios_dir
setenv XIOS_INC $xios_dir/inc
setenv XIOS_LIB $xios_dir/lib
setenv XIOS_EXEC $xios_dir/bin/xios_server.exe

prepend-path PATH $xios_dir/bin

EOF


# create a little script to allow the oasis module to be used by subsequent
# tasks
rm $CYLC_SUITE_RUN_DIR/share/use_xios_mod.sh
cat <<EOF > $CYLC_SUITE_RUN_DIR/share/use_xios_mod.sh
export XIOS_MODULE_USE_PATH=$MODULE_BASE/modules
export XIOS_MODULE_PATH=$xios_mod_version_path/$XIOS_REV
EOF
