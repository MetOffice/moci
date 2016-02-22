#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to diagnose problems with STASH requests, which
reference profile namelists using a shared name variable, since a
misconfiguration will result in failure of the model 

StashProfilesValidate checks for the following conditions:

 #1 There should be no time, domain or use profiles which share the
    same name

 #2 There should be no stash requests providing the name of a time,
    domain or use profile which hasn't been defined

 #3 If a time, domain or usage profile has been defined but isn't being
    included in any stash request (this is only a warning)

StashProfilesRemoveUnused removes the above namelists (those matched by #3)

The two classes share a parent class, StashProfiles, since they use the same
underlying method to extract a structure representing the configuration

"""


import re
import rose.macro
import rose.config

class StashProfiles(rose.macro.MacroBase):
    """Parent class for the other Stash macros"""
    # Names to be used to find the profiles to be checked - the name
    # as it appears in the "namelist:X" section heading and the name
    # of the variable - currently the variable name is the same in
    # both the stash request namelist and the corresponding profiles.
    # This would need extending were that to ever change
    profile_groups = (
        ["time",   "tim_name"],
        ["use",    "use_name"],
        ["domain", "dom_name"],
        )
    
    def scan_requests(self, config):
        """Scan the app for definitions and usages of profile names"""

        # Initialise a pair of dictionaries, each one will store a
        # sub-dictionary for each type of profile, and the sub-dictionaries
        # will have profile names as keys, storing the section names where
        # they are defined or used
        defined_names = {}
        used_names = {}
        for profile, _ in self.profile_groups:
            defined_names[profile] = {}
            used_names[profile] = {}

        # Extract a list of the apps sections and ensure it's in order
        sect_keys = config.value.keys()
        sorter = rose.config.sort_settings
        sect_keys.sort(sorter)

        # Mapping the pattern of namelist to the dictionary in which to store
        # the results, note that the {0:s} indicator will be filled by the
        # name of the profile in the first case
        mapping = [("namelist:{0:s}\(.*?\)$", defined_names),
                   ("namelist:streq\(.*?\)$", used_names)]
        

        # Populate the dictionaries
        for section in sect_keys:
            node = config.get([section])
            for profile, name_var in self.profile_groups:
                for pattern, store_names in mapping:
                    if (isinstance(node.value, dict)
                        and re.match(pattern.format(profile), section)):
                        # If the section matches the pattern, save the set name
                        # to the relevant dictionary unless it is ignored, in
                        # which case skip it
                        name_node = config.get([section, name_var],
                                               no_ignore=False)
                        if not node.is_ignored():
                            name = name_node.value
                            if name in store_names[profile].keys():
                                store_names[profile][name].append(section)
                            else:
                                store_names[profile][name] = [section]
                                
        return defined_names, used_names

class StashProfilesValidate(StashProfiles):
    """Tests that profile names in stash requests exist"""
    def validate(self, config, meta_config=None):
        """Return a list of error, if any."""
        self.reports = []

        # Extract dictionaries of the defined and used profile names
        defined_names, used_names = self.scan_requests(config)

        # Now inspect the differences between the two dictionaries to
        # determine if they are configured properly
        for profile, _ in self.profile_groups:
            for name, sections in defined_names[profile].items():
                # More than one section defining the same profile name
                if len(sections) > 1:
                    for section in sections:
                        self.add_report(section, None, None,
                            "Multiple {0:s} profiles using the same"
                            " name: {1:s}".format(profile, name))
                # Defined section doesn't exist in the requests
                if not name in used_names[profile].keys():
                    self.add_report(sections[0], None, None,
                            "Defined {0:s} profile not required by"
                            " any requests: {1:s}".format(profile, name),
                            is_warning=True)

            for name, sections in used_names[profile].items():
                # An item is used but not defined
                if not name in defined_names[profile].keys():
                    for section in sections:
                        self.add_report(section, None, None,
                                        "Undefined {0:s} profile name in"
                                        " request: {1:s}".format(profile, name))
        return self.reports

class StashProfilesRemoveUnused(StashProfiles):
    """Removes unused stash profile namelists"""
    def transform(self, config, meta_config=None):
        """Remove unused profile namelists"""
        self.reports = []

        # Extract dictionaries of the defined and used profile names
        defined_names, used_names = self.scan_requests(config)

        # Now inspect the differences between the two dictionaries to
        # determine if they are configured properly
        for profile, _ in self.profile_groups:
            for name, sections in defined_names[profile].items():
                # Defined section doesn't exist in the requests
                if not name in used_names[profile].keys():
                    for section in sections:
                        # Remove the elements of the section individually
                        # first (to enable an "undo" to work)
                        for entry in config.get([section]).value.keys():
                            value = config.get_value([section, entry])
                            self.add_report(section, entry, value,
                                "Removing {0:s} from {1:s} profile: {2:s}"
                                .format(entry, profile, name))
                            config.unset([section, entry])
                        # Remove the section itself
                        self.add_report(section, None, None,
                                    "Removing unused {0:s} profile: {1:s}"
                                    .format(profile, name))
                        config.unset([section])

        return config, self.reports

