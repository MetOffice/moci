XIOS/Oasis3-mct build and test scripts README document

Overview
========
The contents of this directory contain scripts to build and test XIOS and 
associated libraries. These include OASIS and NEMO (GYRE configuration). 
The scripts here were written as part of a Rose suite (u-ab692) 
that primarily builds XIOS. In addition to building XIOS, apps in the suite 
also 
* build the OASIS3-MCT library
* run the OASIS3-MCT tutorial application
* run the XIOS "test_complete" test
* build the GYRE configuration of NEMO
* run test GYRE config test

Although primarily intended as part of a Rose suite, the apps can be 
run individually, and scripts are provided to setup up the environment that
would normally be provided by the Rose suite to run individual script.

The scripts are written in Python and should be run using Python 2.7. The 
scripts support and have been tested on multiple platforms.  


Source code overview
====================
The scripts are written in Python. The code is structured as follows

* bin directory - contains the executable scripts which call the main code in 
                  the lib directory

* lib directory - contains most of the core code. These fall into 4 categories:
 * common.py, EnvironmentModules.py - contains common classes and functions
 * *BuildSystem.py - Contains classes for build Oasis3-mct, XIOS & NEMO
 * *TestSystem.py -  Contains classes for testing the libraries & executables
                     that have been built.
 * *ModuleWriter.py - Classes to write environment modules for Oasis3-mct 
                      and XIOS.
* testing  - contains unit tests for the build & test scripts. See 
             "Testing the scripts" section for more info on running tests.
* testing/manual - Contains setup scripts for use by developers to run the 
                   build and test scripts individually. See "Running the 
                   scripts" for more info.
* testing/settings  - Contains settings used by the unit tests and manual 
                      test scripts
* validation - contains small scripts used by rose-stem test suite to validate 
               the output of the tests.

Running the scripts
===================
The scripts can be run individually or as part of a rose suite.

The intended way of running these scripts is as part of a rose suite. To test
the scripts there is a rose stem test as part of the build scripts. To run the 
complete test suite using rose stem use the following command:

rose stem --group=XBS_ALL --opt-conf-key=SYSTEM_NAME

where SYSTEM_NAME is the name of the platform you are running on. Each file in 
the opt sub-directory of the rose-stem directory represents an available 
platform. Alternatively the --opt-conf-key can be ommitted and the 
rose-suite.conf can be be configured accordingly.

There is also a standalone suite intended to be used for deploying the 
libraries. The suite can be found in roses section of the Met Office Science
Repository Service (https://code.metoffice.gov.uk/trac/roses-u/) with suite ID
u-ab692. You can checkout this suite and then run it to build and test the
libraries.

To run them individually, several environment variables need to be set up 
for each each script. In the test/manual directory there are scripts that
setup up the environment and then launch the relevant script. For example
to run the xiosBuild.py script on the Cray XC40 platform, you can run 
the testing/manual/cray_xc40/run_xios_build script. This will launch the setup
the envrionment for and run the bin/xios_build script.


Testing the scripts
===================

Unit tests:
The testing folder contains unit tests for each of the main test scripts for 
each of the supported platforms. To run all the test scripts, you should run one 
of the "run_*_tests" scripts, e.g. run_cray_tests on the Cray XC40. This will
run all the unit tests for that platform. Temporary files for the unit tests
will be put in a scratch directory whose name starts with "scratch_XBStests_".
This directory will be default be created in the users current directory, but
if an argument is supplied to the run test script, that will be used as the
parent directory for the scratch directory. The directory can be deleted when
the tests have run. The unit tests are also run as part of the rose-stem suite.

Functional testing:
To test that the scripts run as intended, the rose test suite can be run.
The rose stem suite provided in the rose-stem directory in the same directory as
this README can be used as described in "Running the scripts" to do functional 
testing.

Alternatively the scripts can be run individually from the command line as 
described in the "Running the scripts" section above. To test all functionality, 
the following scripts should be run:
* testing/manual/crayxc40/run_oasis_build
* testing/manual/crayxc40/run_oasis_test
* testing/manual/crayxc40/run_xios_build
* testing/manual/crayxc40/run_xios_test
* testing/manual/crayxc40/run_nemo_build
* testing/manual/crayxc40/run_nemo_test
