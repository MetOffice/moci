#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Macro for attempting to warn the user if their filename generation patterns
are likely to lead to multiple files with the same names being created
"""

import re
import rose.macro
import rose.config

class OutputNamingCheck(rose.macro.MacroBase):
    """Tests for errors in file naming definitions"""

    def validate(self, config, meta_config=None):
        """Return a list of errors, if any."""
        self.reports = []

        # Start by gathering a dictionary of all known filenames used by the app
        #-----------------------------------------------------------------------
        app_filenames = {}

        # Output streams
        stream_nml_pattern = "namelist:nlstcall_pp\(.*\)$"
        sect_keys = config.value.keys()
        sorter = rose.config.sort_settings
        sect_keys.sort(sorter)
        for section in sect_keys:
            node = config.get([section])
            if (isinstance(node.value, dict)
                and re.match(stream_nml_pattern, section)):

                l_reinit = config.get_value([section, "l_reinit"]) == ".true."
                if l_reinit:
                    app_filenames[section+"=filename_base"] = (
                        config.get_value([section, "filename_base"]))
                else:
                    app_filenames[section+"=filename"] = (
                        config.get_value([section, "filename"]))

        # Dumps
        nlstcgen_section = "namelist:nlstcgen"
        dump_filename = "dump_filename_base"
        dump_file = config.get_value([nlstcgen_section,dump_filename])
        if dump_file:
            app_filenames[nlstcgen_section+"="+dump_filename] = dump_file
        
        # Means
        ppselectim = config.get_value([nlstcgen_section, "ppselectim"])
        if ppselectim:
            ppselectim = ppselectim.split(",")
            for i_mean in range(4):
                if ppselectim[i_mean] == "1":
                    mean_filename = "mean_{0:1d}_filename_base".format(i_mean+1)
                    app_filenames[nlstcgen_section+"="+mean_filename] = (
                        config.get_value(["namelist:nlstcgen", mean_filename]))
                    
                                  
        # Partial sums
        psum_file = "psum_filename_base"
        psum_filename = config.get_value(["namelist:nlstcgen", psum_file])
        if psum_filename is not None:
            app_filenames[nlstcgen_section+"="+psum_file] = psum_filename

        # Other filenames
        nlcfiles_section = "namelist:nlcfiles"
        for keylist, node in config.walk([nlcfiles_section], no_ignore=True):
            app_filenames[nlcfiles_section+"="+keylist[1]] = node.value

        # Now try to check that none of the names clash
        #-----------------------------------------------------------------------

        # Get the list of section names
        sections = app_filenames.keys()
        new_filenames = app_filenames.copy()

        # Filter out characters and sequences which might not be unique
        for section in sections:
            this_filename = app_filenames[section]
            # Filter out the special characters - note that %C is left out
            # of this *on-purpose* because we will consider it unique
            new_filename  = (
                re.sub(r"%([AQR]{0,1}[0-9]*|)[YmdHMSbsT+%Nnz]",r"",this_filename))
            # Filter out strings which look like month or season names - note
            # that we do this with patterns so that each match may only be replaced
            # once (rather than risk a cascading replace wiping out the whole name
            months  = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
            seasons = "jfm|fma|mam|amj|mjj|jja|jas|aso|son|ond|ndj|djf" 
            new_filename = (
                re.sub(r"("+months+"|"+seasons+")",r"",new_filename))
            new_filenames[section] = new_filename

        # Now check each modified name is unique
        for section, filename in new_filenames.items():
            if new_filenames.values().count(filename) > 1:
                clash_list = ""
                for section_2, filename_2 in new_filenames.items():
                    if filename == filename_2 and section_2 != section:
                        clash_list = clash_list + " * " + section_2 + "\n"
                sect, opt = self._get_section_option_from_id(section)
                self.add_report(sect, opt, None,
                                "File naming patterns appear too similar; "
                                "potential clashing of \ngenerated names "
                                "may occur - please carefully check settings.\n"
                                "Name Here: {0:s}\n".format(app_filenames[section]) +
                                "Possible clashing sections: \n{0:s}".format(clash_list),
                                is_warning=True)

        return self.reports
