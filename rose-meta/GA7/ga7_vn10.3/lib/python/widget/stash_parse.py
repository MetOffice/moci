# -*- coding: utf-8 -*-
# *****************************COPYRIGHT*******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT*******************************
import os

import rose.config


class StashMasterParserv1(object):

    """Parse a STASHmaster file.
    
    Initialise with a path to a directory containing STASHmaster files.

    Calling the get_lookup_dict method returns a dictionary
    containing a tree for STASHmaster entry properties, structure:
    section -> item -> property_name -> value

    For example, the following code snippet:
    parser = StashMasterParserv1("/home/me/STASHmaster/")
    lookup_dictionary = parser.get_lookup_dict()
    print lookup_dictionary["0"]["1"][parser.DESC_OPT]
    would print the 'name' string for section 0, item 1.

    """

    DESC_OPT = "name"
    ITEM_OPT = "item"
    RECORD_OPT = "record_{0}"
    SECT_OPT = "sectn"
    STASHMASTER_FILENAME = "STASHmaster_A"
    TEMPLATE = (
r"""1| model | """ + SECT_OPT + "|" + ITEM_OPT + "|" + DESC_OPT + """|
2| space | point | time | grid | levelt | levelf | levell | pseudt | pseudf | pseudl | levcom |
3| option_codes | version_mask | halo |
4| datat | dumpp | pc1-a |
5| rotate | ppfc | user | lbvc | blev | tlev | rblevv | cfll | cfff |""")
    TEMPLATES = [s.split("|") for s in TEMPLATE.replace(" ", "").split("\n")]

    def __init__(self, stashmaster_directory_path):
        self._stash_lookup = {}
        self.parse_stashmaster_files(stashmaster_directory_path)

    def parse_stashmaster_files(self, stashmaster_directory_path):
        """Construct a nested dictionary holding STASHmaster data."""
        self._stash_lookup.clear()
        stash_path = os.path.expanduser(stashmaster_directory_path)
        stash_path = os.path.expandvars(stashmaster_directory_path)
        stashmaster_filename = os.path.join(stash_path,
                                            self.STASHMASTER_FILENAME)
        f = open(stashmaster_filename, 'r')
        lines = f.readlines()
        f.close()
        section = None
        item = None
        props = {}
        for line in lines:
            if len(line) == 0 or not line[0].isdigit():
                continue
            i = int(line[0]) - 1
            if i == 0:  # First line of a record.
                if section is not None and item is not None:
                    self._stash_lookup.setdefault(section, {})
                    self._stash_lookup[section].setdefault(item, {})
                    self._stash_lookup[section][item] = props
                props = {}
            for name, entry in zip(self.TEMPLATES[i][1:],
                                   line.split("|")[1:]):
                if name == self.SECT_OPT:
                    section = entry.strip()
                if name == self.ITEM_OPT:
                    item = entry.strip()
                if name:
                    props[name] = entry.strip()
        if section is not None and item is not None:
            self._stash_lookup.setdefault(section, {})
            self._stash_lookup[section].setdefault(item, {})
            self._stash_lookup[section][item] = props
        return self._stash_lookup

    def get_lookup_dict(self):
        """Return a nested dictionary of stash attributes.

        A particular stash entry has a map of properties under
        self._stash_lookup[section_number][item_number]
        where section_number is the STASH section, and item_number
        the STASH item number.

        For example,
        self._stash_lookup["0"]["1"][DESC_OPT]
        might be something like:
        "U COMPNT OF WIND AFTER TIMESTEP"

        """
        return self._stash_lookup

    __call__ = get_lookup_dict


def get_stashmaster_meta_lookup_dict_v1(stashmaster_meta_path,
                                        stashmaster_meta_filename):
    """Return a nested dictionary with STASHmaster metadata.

    This stores metadata about STASHmaster fields and their values.
    Field metadata is stored as field_name => metadata_property =>
    metadata_value. Field value metadata (for a particular value of
    a field) is under (field_name + "=" + value) =>
    metadata_property => metadata_value.

    For example, if the nested dictionary is called
    'stash_meta_dict':
    stash_meta_dict["grid"]["title"]
    would be something like:
    "Grid code"
    and:
    stash_meta_dict["grid=2"]["description"]
    would be something like:
    "A grid code of 2 means...."

    """
    if stashmaster_meta_path is None:
        return {}
    try:
        config = rose.config.load(
            os.path.join(
                stashmaster_meta_path,
                stashmaster_meta_filename
            )
        )
    except (rose.config.ConfigSyntaxError, IOError, OSError) as e:
        rose.reporter.Reporter()(
            "Error loading STASHmaster metadata resource: " +
            type(e).__name__ + ": " + str(e) + "\n",
            kind=rose.reporter.Reporter.KIND_ERR,
            level=rose.reporter.Reporter.FAIL
        )
        return {}
    stash_meta_dict = {}
    for keys, node in config.walk(no_ignore=True):
        if len(keys) == 2:
            address = keys[0].replace("stashmaster:", "", 1)
            prop = keys[1]
            stash_meta_dict.setdefault(address, {})
            stash_meta_dict[address][prop] = node.value
    return stash_meta_dict
