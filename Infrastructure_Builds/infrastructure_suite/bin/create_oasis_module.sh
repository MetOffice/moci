#!/usr/bin/env bash
#
# NAME: create_oasis_module.sh
#
# DESCRIPTION: Writes the OASIS3-MCT environment module file, and organises
#              the module package directory
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    OASIS_BRANCH
#    OASIS_BUILD_DIR
#    OASIS_MOD_NAME
#    OASIS_MOD_VERSION
#    OASIS_REPOSITORY
#    PRISMPATH
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

oasis_mod_version_path=$OASIS_MOD_NAME/$OASIS_MOD_VERSION/$revision

oasis_dir=$MODULE_BASE/packages/$oasis_mod_version_path/$OASIS_BRANCH
mkdir -p $oasis_dir
oasis_mod_dir=$MODULE_BASE/modules/$oasis_mod_version_path
mkdir -p $oasis_mod_dir

# copy our builds into the module package diectory
cp -r $PRISMPATH/$OASIS_BUILD_DIR/build $oasis_dir/
cp -r $PRISMPATH/$OASIS_BUILD_DIR/lib $oasis_dir/




rm $MODULE_BASE/modules/$oasis_mod_version_path/$OASIS_BRANCH
cat <<EOF >$MODULE_BASE/modules/$oasis_mod_version_path/$OASIS_BRANCH
#%Module1.0
proc ModulesHelp { } {
    puts stderr "Sets up Oasis3-MCT coupler I/O server for use
External URL: $OASIS_REPOSITORY
External branch: $OASIS_BRANCH
Built using Rose suite:
$SUITE_URL
$SUITE_REVISION
"
}

module-whatis The Oasis3-mct coupler for use with weather/climate models

conflict $OASIS_MOD_NAME

set version $OASIS_MOD_VERSION
set module_base $MODULE_BASE
set oasis_dir $oasis_dir

setenv OASIS_ROOT $oasis_dir
setenv prism_path $oasis_dir
setenv OASIS_INC $oasis_dir/inc
setenv OASIS_LIB $oasis_dir/lib
setenv OASIS3_MCT $OASIS_MOD_NAME
setenv OASIS_MODULE_VERSION $OASIS_MOD_VERSION
 
EOF


# create a little script to allow the oasis module to be used by subsequent
# tasks
rm $CYLC_SUITE_RUN_DIR/share/use_oasis_mod.sh
cat <<EOF > $CYLC_SUITE_RUN_DIR/share/use_oasis_mod.sh
export OASIS_MODULE_USE_PATH=$MODULE_BASE/modules
export OASIS_MODULE_PATH=$oasis_mod_version_path/$OASIS_BRANCH
EOF
