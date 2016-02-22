#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to correct STASH namelist indices.

The TidyStashTransform and TidyStashValidate classes attempt to give
checksum-based indices (sort-keys) to STASH-related namelists.

The indices are formed of the first 8 characters of the SHA1 checksum
of the dumped section text as found in a rose config file, excluding
the section header itself and the profile name option (if relevant).

We have 16^8 possible indices for a given namelist name, and the
probability that at least two different namelist contents will have the
same index (collide) follows the birthday problem, assuming a good,
nicely distributed checksum algorithm.

This gives a 50/50 probability of collision in a pool of about 80000
namelists, which a given application is unlikely to have access to.
There is a 1 in 100 chance of collision with about 10000 namelists.
There is a 1 in 24000 chance of collision with about 600. If you have a
'Cannot rename' message with 600 namelists in your file, it is very
very likely that they are identical.

On the command line (in Bash) creating a new index can be done as
follows (vary according to namelist type):
index=$(rose config --file=rose-app.conf 'namelist:time(83)' | \
        sed "/^tim_name/d" | sha1sum)
echo ${index:0:8}

"""


import StringIO
import hashlib
import unittest

import rose.config
import rose.macro


ERROR_ITEMS_OVERWRITE = (
    "Source/domain clash with namelist:items({0}) will cause UM abort")
SECTION_FORMAT = "{0}({1})"
STASH_SECTION_BASES = ["namelist:domain", "namelist:items",
                       "namelist:streq", "namelist:time",
                       "namelist:use"]
STASH_SECTION_BASES_NO_INCLUDE_OPTS_MAP = {"namelist:domain": ["dom_name"],
                                           "namelist:time": ["tim_name"],
                                           "namelist:use": ["use_name"],
                                           "namelist:items": ["ancilfilename"]}
STASH_SECTION_BASES_POINTER_OPT_MAP = {"namelist:domain": "dom_name",
                                       "namelist:time": "tim_name",
                                       "namelist:use": "use_name"}
STASH_SECTION_STREQ_PREFIX = "namelist:streq("


class TidyStashTransform(rose.macro.MacroBase):

    """Correct the index of STASH-related namelists."""

    ABORT_COLLISION = "Cannot rename: hash collision: {0}"
    ABORT_RENAME = "Cannot rename: {0} exists (identical)"
    CHANGE_DELETE = "Deleted - identical to {0}"
    CHANGE_POINTER = "{0} => {1} (identical)"
    CHANGE_RENAME_FROM = "Renamed from {0}"
    CHANGE_RENAME_TO = "Renamed to {0}"
    KEEP_DUPLICATED_NAMELISTS = True

    def transform(self, config, meta_config=None):
        """Rename sections using a hash of their contents."""
        self._resolve_duplicated_namelists(config)
        for data in get_section_new_indices(config):
            section_base, old_index, new_index = data
            no_include_opts = STASH_SECTION_BASES_NO_INCLUDE_OPTS_MAP.get(
                                                        section_base, [])
            old_section = SECTION_FORMAT.format(section_base, old_index)
            new_section = SECTION_FORMAT.format(section_base, new_index)
            if config.get([new_section]) is not None:
                text_old = dump_section(config, old_section,
                                    no_include_opts=no_include_opts)
                text_new = dump_section(config, new_section,
                                    no_include_opts=no_include_opts)
                if text_old != text_new:
                    self.add_report(old_section, None, None,
                                    self.ABORT_COLLISION.format(new_index),
                                    is_warning=True)
                continue
            old_node = config.unset([old_section])
            self.add_report(old_section, None, None,
                            self.CHANGE_RENAME_TO.format(new_section))
            old_id_opt_values = []
            for opt, node in old_node.value.items():
                old_id = rose.CONFIG_DELIMITER.join([old_section, opt])
                new_id = rose.CONFIG_DELIMITER.join([new_section, opt])
                old_id_opt_values.append((old_id, opt, node.value))
            self.add_report(new_section, None, None,
                            self.CHANGE_RENAME_FROM.format(old_section))
            for old_id, opt, value in old_id_opt_values:
                self.add_report(new_section, opt, value,
                                self.CHANGE_RENAME_FROM.format(old_id))
            config.value.update({new_section: old_node})
        self._report_duplicated_items_namelists(config)
        return config, self.reports

    def _resolve_duplicated_namelists(self, config):
        has_unresolved_duplicates = True
        while has_unresolved_duplicates:
            has_unresolved_duplicates = False
            section_new_old_indices = {}
            for data in get_section_new_indices(config):
                section_base, old_index, new_index = data
                no_include_opts = STASH_SECTION_BASES_NO_INCLUDE_OPTS_MAP.get(
                                                         section_base, [])
                pointer_opt = STASH_SECTION_BASES_POINTER_OPT_MAP.get(
                                                            section_base)
                old_section = SECTION_FORMAT.format(section_base, old_index)
                new_section = SECTION_FORMAT.format(section_base, new_index)
                section_new_old_indices.setdefault(section_base, {})
                new_old_indices = section_new_old_indices[section_base]
                if new_index in new_old_indices:
                    other_index = new_old_indices[new_index]
                elif config.get([new_section]) is not None:
                    other_index = new_index
                else:
                    new_old_indices.update({new_index: old_index})
                    continue
                old_section = SECTION_FORMAT.format(section_base, old_index)
                text_old = dump_section(config, old_section,
                                        no_include_opts=no_include_opts)
                other_section = SECTION_FORMAT.format(section_base,
                                                      other_index)
                text_other = dump_section(config, other_section,
                                            no_include_opts=no_include_opts)
                if text_old != text_other:
                    # Not a real duplicate, but a hash collision (rare).
                    self.add_report(old_section, None, None,
                                    self.ABORT_COLLISION.format(other_section),
                                    is_warning=True)
                elif self.KEEP_DUPLICATED_NAMELISTS:
                    # A real duplicated namelist - just warn of it.
                    self.add_report(old_section, None, None,
                                    self.ABORT_RENAME.format(new_section),
                                    is_warning=True)
                else:
                    # A real duplicated namelist - remove it.
                    has_unresolved_duplicates = True
                    if pointer_opt is not None:
                        old_pointer_value = config.get_value(
                                    [old_section, pointer_opt])
                        new_pointer_value = config.get_value(
                                    [other_section, pointer_opt])
                    config.unset([old_section])
                    self.add_report(old_section, None, None,
                                    self.CHANGE_DELETE.format(
                                                other_section))
                    # Adjust any pointer names to use the other section.
                    if pointer_opt is not None:
                        keys_nodes = list(config.walk())
                        keys_nodes.sort(lambda x, y:
                                        rose.config.sort_settings(x[0][0],
                                                                  y[0][0]))
                        for keys, node in keys_nodes:
                            if not keys[0].startswith(
                                           STASH_SECTION_STREQ_PREFIX):
                                continue
                            if (len(keys) == 2 and keys[1] == pointer_opt and
                                node.value == old_pointer_value):
                                node.value = new_pointer_value
                                self.add_report(
                                            keys[0], keys[1], node.value,
                                            self.CHANGE_POINTER.format(
                                                        old_pointer_value,
                                                        new_pointer_value))

    def _report_duplicated_items_namelists(self, config):
        # Report errors for functionally duplicated ITEMS namelists.
        for section, index in get_duplicated_items_problems(config):
            self.add_report(section, None, None,
                            ERROR_ITEMS_OVERWRITE.format(index),
                            is_warning=True)


class TidyStashTransformPruneDuplicated(TidyStashTransform):

   """Correct the index of STASH-related namelists and prune duplicates."""

   KEEP_DUPLICATED_NAMELISTS = False


class TidyStashValidate(rose.macro.MacroBase):

    """Check if STASH-related namelists have the right index."""

    ERROR_INDEX = "Wrong index: {0} should be {1}"
    ERROR_INDEX_CLASH = "Identical sections: "

    def validate(self, config, meta_config=None):
        """Validate indices."""
        for section_base in STASH_SECTION_BASES:
            no_include_opts = STASH_SECTION_BASES_NO_INCLUDE_OPTS_MAP.get(
                                                     section_base, [])
            indices = list(get_all_indices(config, section_base))
            new_index_map = {}
            for index in indices:
                new_index_map.setdefault(index, [])
                new_index_map[index].append(index)
            for old_index, new_index in get_new_indices(config, section_base,
                                                        no_include_opts):
                new_index_map.setdefault(new_index, [])
                new_index_map[new_index].append(old_index)
                if old_index in new_index_map:
                    new_index_map[old_index].pop()
                    if not new_index_map[old_index]:
                        new_index_map.pop(old_index)
                section = SECTION_FORMAT.format(section_base, old_index)
                node = config.get([section])
                new_section = SECTION_FORMAT.format(section_base, new_index)
                node = config.get([new_section])
                if node is not None:
                    # Clash to be picked up later.
                    continue
                self.add_report(section, None, None,
                                self.ERROR_INDEX.format(old_index, new_index))
            for index, same_content_indices in new_index_map.items():
                if len(same_content_indices) > 1:
                    sections = []
                    rep_section = SECTION_FORMAT.format(section_base, index)
                    sections.append(rep_section)
                    for same_content_index in same_content_indices:
                        if same_content_index == index:
                            continue
                        sections.append(SECTION_FORMAT.format(
                                                section_base,
                                                same_content_index))
                    text = self.ERROR_INDEX_CLASH + " == ".join(sections)
                    self.add_report(rep_section, None, None, text)
        self._validate_duplicated_items_namelists(config)
        return self.reports

    def _validate_duplicated_items_namelists(self, config):
        # Report errors for functionally duplicated ITEMS namelists.
        for section, index in get_duplicated_items_problems(config):
            self.add_report(section, None, None,
                            ERROR_ITEMS_OVERWRITE.format(index))


def dump_section(config, section, no_include_opts=None):
    """Return some option=value text used for checksums."""
    new_config = rose.config.ConfigNode()
    if no_include_opts is None:
        no_include_opts = []
    for keylist, opt_node in config.walk([section]):
        option = keylist[1]
        if option in no_include_opts:
            continue
        new_config.value[option] = opt_node
    config_string_file = StringIO.StringIO()
    rose.config.dump(new_config, config_string_file)
    config_string_file.seek(0)
    return config_string_file.read()


def get_all_indices(config, section_base):
    """Return all indices for a section_base in config.

    config should be a rose.config.ConfigNode instance.
    section_base should be the section name without an index - e.g.
    "namelist:foo".

    """
    for section in config.value.keys():
        if not section.startswith(section_base + "("):
            continue
        node = config.get([section])
        if not isinstance(node.value, dict):
            continue
        yield get_index_from_section(section)


def get_duplicated_items_problems(config):
    """Report only-different-by-source-domain items sections."""
    items_str_pure_dict = {}
    items_str_dict = {}
    sections_nodes = list(config.walk())
    sections_nodes.sort(lambda x, y:
                        rose.config.sort_settings(x[0][0], y[0][0]))
    for keys, sect_node in sections_nodes:
        if not isinstance(sect_node.value, dict):
            continue
        if len(keys) != 1:
            continue
        section = keys[0]
        if section.startswith("namelist:items("):
            str_of_namelist = dump_section(
                config, section,
                no_include_opts=["domain", "source"]
            )
            pure_str_of_namelist = dump_section(config, section)
            this_index = get_index_from_section(section)
            items_str_dict.setdefault(str_of_namelist, [])
            items_str_dict[str_of_namelist].append(this_index)
            items_str_pure_dict.setdefault(pure_str_of_namelist, [])
            items_str_pure_dict[pure_str_of_namelist].append(this_index)
    pure_dupl_indices = []
    for indices in items_str_pure_dict.values():
        if len(indices) > 1:
            # These namelists are totally duplicated.
            pure_dupl_indices.extend(indices)
    for str_of_namelist, indices in items_str_dict.items():
        if len(indices) > 1:
            # These namelists are at least functionally duplicated.
            for index in indices[1:]:
                if index in pure_dupl_indices:
                    # It is actually a perfect copy of another items namelist.
                    # This will be reported in the normal duplicate checking.
                    pass
                else:
                    # It is just a functionally duplicated namelist.
                    section = get_section_from_index("namelist:items", index)
                    yield(section, indices[0])


def get_index_from_section(section):
    """Return the index string from an indexed section name."""
    return section.rsplit("(", 1)[1].rstrip(")")


def get_new_indices(config, section_base_name, no_include_opts=None):
    """Return a list of errors, if any."""
    if no_include_opts is None:
        no_include_opts = []
    keys = config.value.keys()
    keys.sort(rose.config.sort_settings)
    for section in keys:
        if not section.startswith(section_base_name + "("):
            continue
        text = dump_section(config, section, no_include_opts)
        old_index = get_index_from_section(section)
        new_index = hashlib.sha1(text).hexdigest()[:8]
        if old_index != new_index:
            yield (old_index, new_index)


def get_section_from_index(section_base, index):
    """Return an indexed section name from a section base name and an index."""
    return section_base + "({0})".format(index)


def get_section_new_indices(config):
    """Get newly calculated indices for the config."""
    for section_base in STASH_SECTION_BASES:
        no_include_opts = STASH_SECTION_BASES_NO_INCLUDE_OPTS_MAP.get(
                                                    section_base, [])
        for old_index, new_index in get_new_indices(config, section_base,
                                                    no_include_opts):
            yield section_base, old_index, new_index


class STASHIndexTestSuite(unittest.TestCase):

    """Class to test the macros."""

    TEST_CONFIG_STRING = """
[namelist:domain_nml]
x=1
y=2

[namelist:foo]
a=1
b=2

# domain(1) (=2)
[namelist:domain(1)]
dom_name='identical1'
imn=0

# domain(2) (=1)
[namelist:domain(2)]
dom_name='identical2'
imn=0

# domain(3)
[namelist:domain(3)]
dom_name='normal1'
imn=1
imsk=1

# domain(4)
[namelist:domain(4)]
dom_name='normal2'
imn=1
imsk=2

# items(1)
[namelist:items(1)]
domain=1
item=302
section=0
source=4

# items(2), functionally equal to items(1)
[namelist:items(2)]
domain=1
item=302
section=0
source=2

# items(3), equal to items(1)
[namelist:items(3)]
domain=1
item=302
section=0
source=4

# streq(1) (if dup removed, =2)
[namelist:streq(1)]
dom_name='identical2'
isec=0
item=2
package='foo'
tim_name='normal1'
use_name='identical1'

# streq(2) (if dup removed, =1)
[namelist:streq(2)]
dom_name='identical1'
isec=0
item=2
package='foo'
tim_name='normal1'
use_name='identical2'

# streq(3) (=4)
[namelist:streq(3)]
dom_name='normal1'
isec=5
item=11
package='foo'
tim_name='normal1'
use_name='identical2'

# streq(4) (=3)
[namelist:streq(4)]
dom_name='normal1'
isec=5
item=11
package='foo'
tim_name='normal1'
use_name='identical2'

# streq(5)
[namelist:streq(5)]
dom_name='normal2'
isec=5
item=11
package='foo'
tim_name='normal2'
use_name='identical1'

# time(1), user-ignored
[!namelist:time(1)]
tim_name='normal1'
iend=9

# time(2)
[namelist:time(2)]
tim_name='normal2'
iend=8

# use(1) (=2)
[namelist:use(1)]
use_name='identical1'
iunt=60

# use(2) (=1)
[namelist:use(2)]
use_name='identical2'
iunt=60

# use(3)
[namelist:use(3)]
use_name='normal1'
!iunt=60
"""

    TEST_TRANSFORM_KEEP_CONFIG_STRING = """# domain(2) (=1)
[namelist:domain(2)]
dom_name='identical2'
imn=0

# domain(4)
[namelist:domain(2af126ec)]
dom_name='normal2'
imn=1
imsk=2

# domain(3)
[namelist:domain(4ccb4417)]
dom_name='normal1'
imn=1
imsk=1

# domain(1) (=2)
[namelist:domain(ed6e1b5e)]
dom_name='identical1'
imn=0

[namelist:domain_nml]
x=1
y=2

[namelist:foo]
a=1
b=2

# items(3), equal to items(1)
[namelist:items(3)]
domain=1
item=302
section=0
source=4

# items(2), functionally equal to items(1)
[namelist:items(521d3f6c)]
domain=1
item=302
section=0
source=2

# items(1)
[namelist:items(97a136a1)]
domain=1
item=302
section=0
source=4

# streq(4) (=3)
[namelist:streq(4)]
dom_name='normal1'
isec=5
item=11
package='foo'
tim_name='normal1'
use_name='identical2'

# streq(5)
[namelist:streq(263d8bd0)]
dom_name='normal2'
isec=5
item=11
package='foo'
tim_name='normal2'
use_name='identical1'

# streq(2) (if dup removed, =1)
[namelist:streq(8f159890)]
dom_name='identical1'
isec=0
item=2
package='foo'
tim_name='normal1'
use_name='identical2'

# streq(1) (if dup removed, =2)
[namelist:streq(94eb9a06)]
dom_name='identical2'
isec=0
item=2
package='foo'
tim_name='normal1'
use_name='identical1'

# streq(3) (=4)
[namelist:streq(f4c34d08)]
dom_name='normal1'
isec=5
item=11
package='foo'
tim_name='normal1'
use_name='identical2'

# time(1), user-ignored
[!namelist:time(16055de9)]
iend=9
tim_name='normal1'

# time(2)
[namelist:time(47fd949e)]
iend=8
tim_name='normal2'

# use(2) (=1)
[namelist:use(2)]
iunt=60
use_name='identical2'

# use(3)
[namelist:use(39bbfabd)]
!iunt=60
use_name='normal1'

# use(1) (=2)
[namelist:use(54db5261)]
iunt=60
use_name='identical1'
"""

    TEST_TRANSFORM_KEEP_OUTPUT = """stash_indices.TidyStashTransform: changes: 74
    namelist:domain(1)=None=None
        Renamed to namelist:domain(ed6e1b5e)
    namelist:domain(ed6e1b5e)=None=None
        Renamed from namelist:domain(1)
    namelist:domain(ed6e1b5e)=dom_name='identical1'
        Renamed from namelist:domain(1)=dom_name
    namelist:domain(ed6e1b5e)=imn=0
        Renamed from namelist:domain(1)=imn
    namelist:domain(3)=None=None
        Renamed to namelist:domain(4ccb4417)
    namelist:domain(4ccb4417)=None=None
        Renamed from namelist:domain(3)
    namelist:domain(4ccb4417)=imsk=1
        Renamed from namelist:domain(3)=imsk
    namelist:domain(4ccb4417)=dom_name='normal1'
        Renamed from namelist:domain(3)=dom_name
    namelist:domain(4ccb4417)=imn=1
        Renamed from namelist:domain(3)=imn
    namelist:domain(4)=None=None
        Renamed to namelist:domain(2af126ec)
    namelist:domain(2af126ec)=None=None
        Renamed from namelist:domain(4)
    namelist:domain(2af126ec)=imsk=2
        Renamed from namelist:domain(4)=imsk
    namelist:domain(2af126ec)=dom_name='normal2'
        Renamed from namelist:domain(4)=dom_name
    namelist:domain(2af126ec)=imn=1
        Renamed from namelist:domain(4)=imn
    namelist:items(1)=None=None
        Renamed to namelist:items(97a136a1)
    namelist:items(97a136a1)=None=None
        Renamed from namelist:items(1)
    namelist:items(97a136a1)=item=302
        Renamed from namelist:items(1)=item
    namelist:items(97a136a1)=domain=1
        Renamed from namelist:items(1)=domain
    namelist:items(97a136a1)=section=0
        Renamed from namelist:items(1)=section
    namelist:items(97a136a1)=source=4
        Renamed from namelist:items(1)=source
    namelist:items(2)=None=None
        Renamed to namelist:items(521d3f6c)
    namelist:items(521d3f6c)=None=None
        Renamed from namelist:items(2)
    namelist:items(521d3f6c)=item=302
        Renamed from namelist:items(2)=item
    namelist:items(521d3f6c)=domain=1
        Renamed from namelist:items(2)=domain
    namelist:items(521d3f6c)=section=0
        Renamed from namelist:items(2)=section
    namelist:items(521d3f6c)=source=2
        Renamed from namelist:items(2)=source
    namelist:streq(1)=None=None
        Renamed to namelist:streq(94eb9a06)
    namelist:streq(94eb9a06)=None=None
        Renamed from namelist:streq(1)
    namelist:streq(94eb9a06)=package='foo'
        Renamed from namelist:streq(1)=package
    namelist:streq(94eb9a06)=tim_name='normal1'
        Renamed from namelist:streq(1)=tim_name
    namelist:streq(94eb9a06)=use_name='identical1'
        Renamed from namelist:streq(1)=use_name
    namelist:streq(94eb9a06)=dom_name='identical2'
        Renamed from namelist:streq(1)=dom_name
    namelist:streq(94eb9a06)=isec=0
        Renamed from namelist:streq(1)=isec
    namelist:streq(94eb9a06)=item=2
        Renamed from namelist:streq(1)=item
    namelist:streq(2)=None=None
        Renamed to namelist:streq(8f159890)
    namelist:streq(8f159890)=None=None
        Renamed from namelist:streq(2)
    namelist:streq(8f159890)=package='foo'
        Renamed from namelist:streq(2)=package
    namelist:streq(8f159890)=tim_name='normal1'
        Renamed from namelist:streq(2)=tim_name
    namelist:streq(8f159890)=use_name='identical2'
        Renamed from namelist:streq(2)=use_name
    namelist:streq(8f159890)=dom_name='identical1'
        Renamed from namelist:streq(2)=dom_name
    namelist:streq(8f159890)=isec=0
        Renamed from namelist:streq(2)=isec
    namelist:streq(8f159890)=item=2
        Renamed from namelist:streq(2)=item
    namelist:streq(3)=None=None
        Renamed to namelist:streq(f4c34d08)
    namelist:streq(f4c34d08)=None=None
        Renamed from namelist:streq(3)
    namelist:streq(f4c34d08)=package='foo'
        Renamed from namelist:streq(3)=package
    namelist:streq(f4c34d08)=tim_name='normal1'
        Renamed from namelist:streq(3)=tim_name
    namelist:streq(f4c34d08)=use_name='identical2'
        Renamed from namelist:streq(3)=use_name
    namelist:streq(f4c34d08)=dom_name='normal1'
        Renamed from namelist:streq(3)=dom_name
    namelist:streq(f4c34d08)=isec=5
        Renamed from namelist:streq(3)=isec
    namelist:streq(f4c34d08)=item=11
        Renamed from namelist:streq(3)=item
    namelist:streq(5)=None=None
        Renamed to namelist:streq(263d8bd0)
    namelist:streq(263d8bd0)=None=None
        Renamed from namelist:streq(5)
    namelist:streq(263d8bd0)=package='foo'
        Renamed from namelist:streq(5)=package
    namelist:streq(263d8bd0)=tim_name='normal2'
        Renamed from namelist:streq(5)=tim_name
    namelist:streq(263d8bd0)=use_name='identical1'
        Renamed from namelist:streq(5)=use_name
    namelist:streq(263d8bd0)=dom_name='normal2'
        Renamed from namelist:streq(5)=dom_name
    namelist:streq(263d8bd0)=isec=5
        Renamed from namelist:streq(5)=isec
    namelist:streq(263d8bd0)=item=11
        Renamed from namelist:streq(5)=item
    namelist:time(1)=None=None
        Renamed to namelist:time(16055de9)
    namelist:time(16055de9)=None=None
        Renamed from namelist:time(1)
    namelist:time(16055de9)=tim_name='normal1'
        Renamed from namelist:time(1)=tim_name
    namelist:time(16055de9)=iend=9
        Renamed from namelist:time(1)=iend
    namelist:time(2)=None=None
        Renamed to namelist:time(47fd949e)
    namelist:time(47fd949e)=None=None
        Renamed from namelist:time(2)
    namelist:time(47fd949e)=tim_name='normal2'
        Renamed from namelist:time(2)=tim_name
    namelist:time(47fd949e)=iend=8
        Renamed from namelist:time(2)=iend
    namelist:use(1)=None=None
        Renamed to namelist:use(54db5261)
    namelist:use(54db5261)=None=None
        Renamed from namelist:use(1)
    namelist:use(54db5261)=iunt=60
        Renamed from namelist:use(1)=iunt
    namelist:use(54db5261)=use_name='identical1'
        Renamed from namelist:use(1)=use_name
    namelist:use(3)=None=None
        Renamed to namelist:use(39bbfabd)
    namelist:use(39bbfabd)=None=None
        Renamed from namelist:use(3)
    namelist:use(39bbfabd)=iunt=60
        Renamed from namelist:use(3)=iunt
    namelist:use(39bbfabd)=use_name='normal1'
        Renamed from namelist:use(3)=use_name
stash_indices.TidyStashTransform: warnings: 5
    namelist:domain(2)=None=None
        Cannot rename: namelist:domain(ed6e1b5e) exists (identical)
    namelist:items(3)=None=None
        Cannot rename: namelist:items(97a136a1) exists (identical)
    namelist:streq(4)=None=None
        Cannot rename: namelist:streq(f4c34d08) exists (identical)
    namelist:use(2)=None=None
        Cannot rename: namelist:use(54db5261) exists (identical)
    namelist:items(521d3f6c)=None=None
        Source/domain clash with namelist:items(3) will cause UM abort
"""

    TEST_TRANSFORM_CONFIG_STRING = """# domain(4)
[namelist:domain(2af126ec)]
dom_name='normal2'
imn=1
imsk=2

# domain(3)
[namelist:domain(4ccb4417)]
dom_name='normal1'
imn=1
imsk=1

# domain(1) (=2)
[namelist:domain(ed6e1b5e)]
dom_name='identical1'
imn=0

[namelist:domain_nml]
x=1
y=2

[namelist:foo]
a=1
b=2

# items(2), functionally equal to items(1)
[namelist:items(521d3f6c)]
domain=1
item=302
section=0
source=2

# items(1)
[namelist:items(97a136a1)]
domain=1
item=302
section=0
source=4

# streq(3) (=4)
[namelist:streq(1c83d5ad)]
dom_name='normal1'
isec=5
item=11
package='foo'
tim_name='normal1'
use_name='identical1'

# streq(5)
[namelist:streq(263d8bd0)]
dom_name='normal2'
isec=5
item=11
package='foo'
tim_name='normal2'
use_name='identical1'

# streq(1) (if dup removed, =2)
[namelist:streq(c2f44d54)]
dom_name='identical1'
isec=0
item=2
package='foo'
tim_name='normal1'
use_name='identical1'

# time(1), user-ignored
[!namelist:time(16055de9)]
iend=9
tim_name='normal1'

# time(2)
[namelist:time(47fd949e)]
iend=8
tim_name='normal2'

# use(3)
[namelist:use(39bbfabd)]
!iunt=60
use_name='normal1'

# use(1) (=2)
[namelist:use(54db5261)]
iunt=60
use_name='identical1'
"""

    TEST_TRANSFORM_OUTPUT = """stash_indices.TidyStashTransform: changes: 74
    namelist:domain(2)=None=None
        Deleted - identical to namelist:domain(1)
    namelist:streq(1)=dom_name='identical1'
        'identical2' => 'identical1' (identical)
    namelist:items(3)=None=None
        Deleted - identical to namelist:items(1)
    namelist:streq(4)=None=None
        Deleted - identical to namelist:streq(3)
    namelist:use(2)=None=None
        Deleted - identical to namelist:use(1)
    namelist:streq(2)=use_name='identical1'
        'identical2' => 'identical1' (identical)
    namelist:streq(3)=use_name='identical1'
        'identical2' => 'identical1' (identical)
    namelist:streq(2)=None=None
        Deleted - identical to namelist:streq(1)
    namelist:domain(1)=None=None
        Renamed to namelist:domain(ed6e1b5e)
    namelist:domain(ed6e1b5e)=None=None
        Renamed from namelist:domain(1)
    namelist:domain(ed6e1b5e)=dom_name='identical1'
        Renamed from namelist:domain(1)=dom_name
    namelist:domain(ed6e1b5e)=imn=0
        Renamed from namelist:domain(1)=imn
    namelist:domain(3)=None=None
        Renamed to namelist:domain(4ccb4417)
    namelist:domain(4ccb4417)=None=None
        Renamed from namelist:domain(3)
    namelist:domain(4ccb4417)=imsk=1
        Renamed from namelist:domain(3)=imsk
    namelist:domain(4ccb4417)=dom_name='normal1'
        Renamed from namelist:domain(3)=dom_name
    namelist:domain(4ccb4417)=imn=1
        Renamed from namelist:domain(3)=imn
    namelist:domain(4)=None=None
        Renamed to namelist:domain(2af126ec)
    namelist:domain(2af126ec)=None=None
        Renamed from namelist:domain(4)
    namelist:domain(2af126ec)=imsk=2
        Renamed from namelist:domain(4)=imsk
    namelist:domain(2af126ec)=dom_name='normal2'
        Renamed from namelist:domain(4)=dom_name
    namelist:domain(2af126ec)=imn=1
        Renamed from namelist:domain(4)=imn
    namelist:items(1)=None=None
        Renamed to namelist:items(97a136a1)
    namelist:items(97a136a1)=None=None
        Renamed from namelist:items(1)
    namelist:items(97a136a1)=item=302
        Renamed from namelist:items(1)=item
    namelist:items(97a136a1)=domain=1
        Renamed from namelist:items(1)=domain
    namelist:items(97a136a1)=section=0
        Renamed from namelist:items(1)=section
    namelist:items(97a136a1)=source=4
        Renamed from namelist:items(1)=source
    namelist:items(2)=None=None
        Renamed to namelist:items(521d3f6c)
    namelist:items(521d3f6c)=None=None
        Renamed from namelist:items(2)
    namelist:items(521d3f6c)=item=302
        Renamed from namelist:items(2)=item
    namelist:items(521d3f6c)=domain=1
        Renamed from namelist:items(2)=domain
    namelist:items(521d3f6c)=section=0
        Renamed from namelist:items(2)=section
    namelist:items(521d3f6c)=source=2
        Renamed from namelist:items(2)=source
    namelist:streq(1)=None=None
        Renamed to namelist:streq(c2f44d54)
    namelist:streq(c2f44d54)=None=None
        Renamed from namelist:streq(1)
    namelist:streq(c2f44d54)=package='foo'
        Renamed from namelist:streq(1)=package
    namelist:streq(c2f44d54)=tim_name='normal1'
        Renamed from namelist:streq(1)=tim_name
    namelist:streq(c2f44d54)=use_name='identical1'
        Renamed from namelist:streq(1)=use_name
    namelist:streq(c2f44d54)=dom_name='identical1'
        Renamed from namelist:streq(1)=dom_name
    namelist:streq(c2f44d54)=isec=0
        Renamed from namelist:streq(1)=isec
    namelist:streq(c2f44d54)=item=2
        Renamed from namelist:streq(1)=item
    namelist:streq(3)=None=None
        Renamed to namelist:streq(1c83d5ad)
    namelist:streq(1c83d5ad)=None=None
        Renamed from namelist:streq(3)
    namelist:streq(1c83d5ad)=package='foo'
        Renamed from namelist:streq(3)=package
    namelist:streq(1c83d5ad)=tim_name='normal1'
        Renamed from namelist:streq(3)=tim_name
    namelist:streq(1c83d5ad)=use_name='identical1'
        Renamed from namelist:streq(3)=use_name
    namelist:streq(1c83d5ad)=dom_name='normal1'
        Renamed from namelist:streq(3)=dom_name
    namelist:streq(1c83d5ad)=isec=5
        Renamed from namelist:streq(3)=isec
    namelist:streq(1c83d5ad)=item=11
        Renamed from namelist:streq(3)=item
    namelist:streq(5)=None=None
        Renamed to namelist:streq(263d8bd0)
    namelist:streq(263d8bd0)=None=None
        Renamed from namelist:streq(5)
    namelist:streq(263d8bd0)=package='foo'
        Renamed from namelist:streq(5)=package
    namelist:streq(263d8bd0)=tim_name='normal2'
        Renamed from namelist:streq(5)=tim_name
    namelist:streq(263d8bd0)=use_name='identical1'
        Renamed from namelist:streq(5)=use_name
    namelist:streq(263d8bd0)=dom_name='normal2'
        Renamed from namelist:streq(5)=dom_name
    namelist:streq(263d8bd0)=isec=5
        Renamed from namelist:streq(5)=isec
    namelist:streq(263d8bd0)=item=11
        Renamed from namelist:streq(5)=item
    namelist:time(1)=None=None
        Renamed to namelist:time(16055de9)
    namelist:time(16055de9)=None=None
        Renamed from namelist:time(1)
    namelist:time(16055de9)=tim_name='normal1'
        Renamed from namelist:time(1)=tim_name
    namelist:time(16055de9)=iend=9
        Renamed from namelist:time(1)=iend
    namelist:time(2)=None=None
        Renamed to namelist:time(47fd949e)
    namelist:time(47fd949e)=None=None
        Renamed from namelist:time(2)
    namelist:time(47fd949e)=tim_name='normal2'
        Renamed from namelist:time(2)=tim_name
    namelist:time(47fd949e)=iend=8
        Renamed from namelist:time(2)=iend
    namelist:use(1)=None=None
        Renamed to namelist:use(54db5261)
    namelist:use(54db5261)=None=None
        Renamed from namelist:use(1)
    namelist:use(54db5261)=iunt=60
        Renamed from namelist:use(1)=iunt
    namelist:use(54db5261)=use_name='identical1'
        Renamed from namelist:use(1)=use_name
    namelist:use(3)=None=None
        Renamed to namelist:use(39bbfabd)
    namelist:use(39bbfabd)=None=None
        Renamed from namelist:use(3)
    namelist:use(39bbfabd)=iunt=60
        Renamed from namelist:use(3)=iunt
    namelist:use(39bbfabd)=use_name='normal1'
        Renamed from namelist:use(3)=use_name
stash_indices.TidyStashTransform: warnings: 1
    namelist:items(97a136a1)=None=None
        Source/domain clash with namelist:items(521d3f6c) will cause UM abort
"""

    TEST_VALIDATE_OUTPUT = """stash_indices.TidyStashValidate: issues: 22
    namelist:domain(1)=None=None
        Wrong index: 1 should be ed6e1b5e
    namelist:domain(2)=None=None
        Wrong index: 2 should be ed6e1b5e
    namelist:domain(3)=None=None
        Wrong index: 3 should be 4ccb4417
    namelist:domain(4)=None=None
        Wrong index: 4 should be 2af126ec
    namelist:domain(ed6e1b5e)=None=None
        Identical sections: namelist:domain(ed6e1b5e) == namelist:domain(1) == namelist:domain(2)
    namelist:items(1)=None=None
        Wrong index: 1 should be 97a136a1
    namelist:items(2)=None=None
        Wrong index: 2 should be 521d3f6c
    namelist:items(3)=None=None
        Wrong index: 3 should be 97a136a1
    namelist:items(97a136a1)=None=None
        Identical sections: namelist:items(97a136a1) == namelist:items(1) == namelist:items(3)
    namelist:streq(1)=None=None
        Wrong index: 1 should be 94eb9a06
    namelist:streq(2)=None=None
        Wrong index: 2 should be 8f159890
    namelist:streq(3)=None=None
        Wrong index: 3 should be f4c34d08
    namelist:streq(4)=None=None
        Wrong index: 4 should be f4c34d08
    namelist:streq(5)=None=None
        Wrong index: 5 should be 263d8bd0
    namelist:streq(f4c34d08)=None=None
        Identical sections: namelist:streq(f4c34d08) == namelist:streq(3) == namelist:streq(4)
    namelist:time(1)=None=None
        Wrong index: 1 should be 16055de9
    namelist:time(2)=None=None
        Wrong index: 2 should be 47fd949e
    namelist:use(1)=None=None
        Wrong index: 1 should be 54db5261
    namelist:use(2)=None=None
        Wrong index: 2 should be 54db5261
    namelist:use(3)=None=None
        Wrong index: 3 should be 39bbfabd
    namelist:use(54db5261)=None=None
        Identical sections: namelist:use(54db5261) == namelist:use(1) == namelist:use(2)
    namelist:items(2)=None=None
        Source/domain clash with namelist:items(1) will cause UM abort
"""

    def setupTests(self):
        import rose.macro

    def test_transform_keep(self):
        """Test the Transform macro (keep duplicated namelists)."""
        setup_config = self._get_setup_config()
        meta_config = rose.config.ConfigNode()
        new_config, reports = TidyStashTransform().transform(
                                       setup_config)
        ctrl_report_string = self.TEST_TRANSFORM_KEEP_OUTPUT
        my_report_string = rose.macro.get_reports_as_text(
                                            reports,
                                            "stash_indices.TidyStashTransform",
                                            is_from_transform=True)
        self.assertEqual(my_report_string, ctrl_report_string)
        f = StringIO.StringIO()
        rose.config.dump(new_config, f)
        f.seek(0)
        my_config_string = f.read()
        ctrl_config_string = self.TEST_TRANSFORM_KEEP_CONFIG_STRING
        self.assertEqual(my_config_string, ctrl_config_string)

    def test_transform_no_keep(self):
        """Test the Transform macro (delete duplicated namelists)."""
        setup_config = self._get_setup_config()
        meta_config = rose.config.ConfigNode()
        new_config, reports = TidyStashTransformPruneDuplicated().transform(
                                                     setup_config)
        ctrl_report_string = self.TEST_TRANSFORM_OUTPUT
        my_report_string = rose.macro.get_reports_as_text(
                                            reports,
                                            "stash_indices.TidyStashTransform",
                                            is_from_transform=True)
        self.assertEqual(my_report_string, ctrl_report_string)
        f = StringIO.StringIO()
        rose.config.dump(new_config, f)
        f.seek(0)
        my_config_string = f.read()
        ctrl_config_string = self.TEST_TRANSFORM_CONFIG_STRING
        self.assertEqual(my_config_string, ctrl_config_string)

    def test_validate(self):
        """Test the Validator macro."""
        setup_config = self._get_setup_config()
        meta_config = rose.config.ConfigNode()
        reports = TidyStashValidate().validate(setup_config, meta_config)
        ctrl_report_string = self.TEST_VALIDATE_OUTPUT
        my_report_string = rose.macro.get_reports_as_text(
                                            reports,
                                            "stash_indices.TidyStashValidate",
                                            is_from_transform=False)
        self.assertEqual(my_report_string, ctrl_report_string)

    def _get_setup_config(self):
        f = StringIO.StringIO(self.TEST_CONFIG_STRING)
        return rose.config.load(f)


if __name__ == "__main__":
    import unittest
    unittest.main()
