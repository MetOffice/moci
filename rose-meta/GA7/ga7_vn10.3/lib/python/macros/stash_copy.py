#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to Import and Export STASH related namelists
   from UM rose-app.conf files and all optional configurations.
"""

import re
import rose.macro
import rose.config
import os.path

# Pattern match for the namelists recognised as STASH namelists
IS_STASH_NL = re.compile(r'namelist:('
                            'streq'
                           '|use'
                           '|domain'
                           '|time'
                           '|nlstcall_pp'
                               ')')


class STASHExport(rose.macro.MacroBase):
    """Exports all the STASH related namelists found in the app config"""

    def transform(self, config, meta_config=None,
                  stash_export_filename='STASHexport.ini'):
        """ Dumps STASH related namelists to a file :
            Whilst this macro doesn't alter the config, it is a transform
            macro and not a validate one specifically so it doesn't get run
            by \"validate all\""""

        self.reports = []
        temp_config = rose.config.ConfigNode()
        namelist_count = 0

        # Walk through a config looking for STASH namelists.
        # Add STASH namelists to a new config and then dump that out to file
        for node_key, node in config.walk(no_ignore=False):
            if not isinstance(node.value, dict):
                continue

            if IS_STASH_NL.match(node_key[0]):
                temp_config.set(keys=node_key, value=node.value,
                                state=node.state, comments=node.comments)
                namelist_count += 1

        rose.config.dump(temp_config, stash_export_filename)
        print "Exported {0:d} STASH related namelists".format(namelist_count)

        return config, self.reports


class STASHImport(rose.macro.MacroBase):
    """Import STASH from a user specified UM rose-app.conf"""

    def transform(self, config, meta_config=None, stash_donor_job=None):
        """Import STASH namelists from a file of ini/config format.
           Overwrites any pre-existing STASH namelists in the current
           configuration"""

        self.reports = []
 
        # The macro will prompt the user for the path to donor config.
        # If supplied a directory use it to construct a path to a rose-app.conf
        # file therein.
        # Otherwise assume path supplied is to the file to be used.
        donor_job_fullpath = os.path.realpath(stash_donor_job)
        if os.path.isdir(donor_job_fullpath):
            donor_job_filename = os.path.join(donor_job_fullpath,
                                              "rose-app.conf")
        else:
            donor_job_filename = donor_job_fullpath

        # Load the donor rose-app config or other ini format file
        if os.path.exists(donor_job_filename):
            donor_config = rose.config.load(donor_job_filename)
        else:
            error_msg = ("Donor configuration : Not found at : \"{0:s}\"".format
                         (donor_job_filename))
            raise Exception(error_msg)

        # Delete the existing STASH records.
        for node_key, node in config.walk(no_ignore=False):
            if not isinstance(node.value, dict):
                continue

            if IS_STASH_NL.match(node_key[0]):
                message = '{0:s} will be deleted.'.format(node_key[0])
                self.add_report(node_key[0], None, None, message)
                config.unset(keys=[node_key[0]])

        # Add STASH nodes from donor config to existing config
        for node_key, node in donor_config.walk(no_ignore=False):
            if not isinstance(node.value, dict):
                continue

            if IS_STASH_NL.match(node_key[0]):
                message = '{0:s} will be added.'.format(node_key[0])
                self.add_report(node_key[0], None, None, message)
                config.set(keys=node_key, value=node.value,
                           state=node.state, comments=node.comments)

        return config, self.reports
