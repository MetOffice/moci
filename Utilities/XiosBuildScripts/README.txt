XIOS build and test scripts README document

Overview
========
The contents of this directory contain scripts to build and test XIOS and 
associated libraries. These include OASIS and NEMO (GYRE configuration). 
The scripts here were to written as part of a Rose suite (originally mi-ad949) 
that primarily builds XIOS. In addition to building XIOS, apps in the suite 
also 
* build the OASIS3-MCT library
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

* xiosBuild.py - Script to build XIOS library and create an environment module for XIOS
* xiosTest.py - Script to run the "test_complete" test found in the XIOS 
                repository.
* nemoBuild.py - script to build the NEMO application using the GYRE 
                 configuration
* nemoTest.py - script to test NEMO with XIOS using the GYRE configuration
* EnvironmentModules.py - Classes to write out environment module files

* testing  - contains unit tests for the build & test scripts. See 
             "Testing the scripts" section for more info on running tests.
* setupScripts - contains shell script to set up environment to run the 
                 the build and test scripts from the command line. The 
                 scripts are designed to run as part of a Rose suite. 
                 See setupScripts/README.txt for more info


Running the scripts
===================
The scripts can be run individually or as part of a rose suite.

The intended way of running these scripts is as part of a rose suite. To test
the scripts there is a rose stem test as part of the build scripts. 

!!IMPORTANT INFORMATION!!
In the current version of Rose (2015.06.0), in order for rose stem to work, the
checkout directory from the repository HAS to be be the one immediately
above the level of the directory called rose-stem. If you check out a higher 
level, for example checking out the root directory, rose stem will fail or run
the wrong rose stem test. The level at which you check out the scripts to run
rose stem should be the directory that contains this README file.

To run rose stem that you have checked out correctly (see above paragraph) you 
run the command "rose stem --group=test_nemo_gyre". This will run the complete 
test suite. You can also use "--group=test_xios" to not build or test the NEMO
GYRE configuration.

To run them individually, several environment variables need to be set up 
for each each script. These can be set up by running a script  in the 
setupScripts/ directory. See setupScripts/README.txt for more info.



Testing the scripts
===================

Unit tests:
The testing folder contains unit tests for each of the main test scripts for 
each of the supported platforms. To run all the test scripts, you should run one 
of the "run*Tests" scripts, e.g. runCrayTests on the Cray XC40. This will
run all the unit tests for that platform. Temporary files for the unit tests
will be put in a scratch directory whose name starts with "scratch_XBStests_".
This directory will be default be created in the users current directory, but
if an argument is supplied to the run test script, that will be used as the
parent directory for the scratch directory. The directory can be deleted when
the tests have run.

Functional testing:
To test that the scripts run as intended, the rose test suite can be run.
The rose stem suite provided in the rose-stem directory in the same directory as
this README can be used as described in "Running the scripts" to do functional 
testing.

Alternatively the scripts can be run individually from the command line as 
described in the "Running the scripts" section above. To test all functionality, 
the following scripts should be run. When running
* oasisBuild.py
* xiosBuild.py
* xiosTest.py 
* nemoBuild.py
* nemoTest.py



