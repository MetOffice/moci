#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to diagnose problems with output stream
definitions and usage profiles, since a misconfiguration will result
in failure of the model or undesired output problems

It checks for the following conditions:

 #1 There should be no usage namelists attempting to send output data
    to an output stream which hasn't been defined

 #2 There cannot be multiple definitions with the same file_id

 #3 If an output stream has been defined but no output data is being
    sent there it might be a mistake (this is only a warning)

"""


import re
import rose.macro
import rose.config

class OutputStreamValidate(rose.macro.MacroBase):
    """Tests for errors in output stream definitions"""

    def validate(self, config, meta_config=None):
        """Return a list of errors, if any."""
        self.reports = []
        
        # Patterns which identify the usage and output stream namelists
        use_nml_pattern    = "namelist:use\(.*\)$"
        stream_nml_pattern = "namelist:nlstcall_pp\(.*\)$"

        # Dictionaries to store the used ids - the keys will be the file_ids
        # (which should be unique), and the values will be a list of sections
        # referencing the given file_id)
        use_ids = {}
        stream_ids = {}

        # Setup a loop over all sections and filter out the global sections
        # and any which don't match either of our patterns above
        sect_keys = config.value.keys()
        sorter = rose.config.sort_settings
        sect_keys.sort(sorter)
        for section in sect_keys:
            node = config.get([section])
            if (not isinstance(node.value, dict)
                or (not re.match(use_nml_pattern, section)
                    and not re.match(stream_nml_pattern, section))):
                continue

            # Build up lists of file_ids for which streams are defined and which
            # are used
            for pattern, ids in zip([use_nml_pattern, stream_nml_pattern],
                                    [use_ids, stream_ids]):
                if re.match(pattern, section):
                    file_id = config.get_value([section, "file_id"])
                    
                    # Note: for the usage profiles it is valid for there to be
                    # no file_id defined (if the usage requests is sending to
                    # the dump or climate meaning output)
                    if file_id:
                        if file_id not in ids.keys():
                            ids[file_id] = [section]
                        else:
                            ids[file_id].append(section)
                
        # Examine the lists of used ids
        for use_id, sections in use_ids.items():

            # All streams named by usage namelists should be defined
            if use_id not in stream_ids.keys():
                for section in sections:
                    self.add_report(section, None, None, 
                                    "Usage request sends to undefined "+
                                    "output stream file_id ({0:s})".format(use_id))

        # Examine the list of defined ids
        for stream_id, sections in stream_ids.items():
            # There should only be one of each id defined in the output streams
            if len(sections) > 1:
                for section in sections:
                    self.add_report(section, None, None,
                                    "Multiple output streams using the "+
                                    "same file_id ({0:s})".format(stream_id))

            # Warning (non fatal) if a stream is defined but not used
            if stream_id not in use_ids.keys():
                for section in sections:
                    self.add_report(section, None, None,
                                    "Defined output stream has no output "+
                                    "directed to it ({0:s})".format(stream_id), 
                                    is_warning=True)

                

        return self.reports
                
                
        
