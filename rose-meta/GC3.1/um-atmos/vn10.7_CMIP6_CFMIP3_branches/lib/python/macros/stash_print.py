#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to Print STASH related namelists
   from UM rose-app.conf files and all optional configurations.
   STASHPrint is used as a base class so that variations of 'style'
   can use the same basic print engine but override the formatting
   for the desired purpose.
"""

import re
import os
import sys
import rose.macro
import stash_handling_funcs as stash
META_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#META_DIR = os.path.dirname(os.path.dirname(META_PYTHON_DIR))
sys.path.append(META_PYTHON_DIR)
import widget.stash_parse
import widget.stash


class STASHPrint(rose.macro.MacroBase):
    """Print out the STASH requests, and domain, time and usage profiles,
       from a job in human readable form. Plain text format."""

    streq_format_string = (" {0:>7s} : {1:>4s} : {2:36s} : {3:14s}"
                           " : {4:14s} : {5:14s} : {6:20s} : {7:8s}")
    streq_header_format_string = "\n{0:s}\n"
    streq_footer_format_string = "\n{0:s}\n"

    domain_format_string = (" {0:12s} : {1:53} : {2:30s} : {3:50s}"
                            " : {4:15s} : {5:10s} : {6:8s} : {7:8s}")
    domain_header_format_string = "\n{0:s}\n"
    domain_footer_format_string = "\n{0:s}\n"

    time_format_string = (" {0:12s} : {1:10s} : {2:70s} : {3:12s}"
                          " : {4:14s} : {5:12s} : {6:12s}")
    time_header_format_string = "\n{0:s}\n"
    time_footer_format_string = "\n{0:s}\n"

    use_header_format_string = "\n{0:s}\n"
    use_format_string = (" {0:12s} : {1:32s} : {2:18s} : {3:25s} : {4:75s} :"
                         " {5:20s} : {6:16s} : {7:8s}")
    use_footer_format_string = "\n{0:s}\n"

    def transform(self, config, meta_config=None):
        """This transform macro prints out the STASH requests and profiles
           from a UM rose-app configuration."""

        self.reports = []

        stuff_to_find = [(stash.IS_STASH_NL, None, None)]
        messages, stash_config = stash.filter_on_match(stuff_to_find, config)

        # output the table of STASH requests
        self.print_streq_header()

        stuff_to_find = [(stash.IS_STASH_STREQ_NL, None, None)]
        messages, temp_config = stash.filter_on_match(stuff_to_find,
                                                      stash_config)

        stash_list = get_stash_reqs_list(temp_config)

        for stash_req in sorted(stash_list, key=self.int_keys_of_str_tuple):
            self.print_streq_entry(stash_req)

        self.print_streq_footer()

        # output the table of domains
        self.print_domain_header()

        stuff_to_find = [(stash.IS_STASH_DOMAIN_NL, None, None)]
        messages, temp_config = stash.filter_on_match(stuff_to_find,
                                                      stash_config)

        domains_list = get_stash_domains_list(temp_config)

        for domain in sorted(domains_list):
            self.print_domain_entry(domain)

        self.print_domain_footer()

        # output the table of times
        self.print_time_header()

        stuff_to_find = [(stash.IS_STASH_TIME_NL, None, None)]
        messages, temp_config = stash.filter_on_match(stuff_to_find,
                                                      stash_config)

        times_list = get_stash_times_list(temp_config)

        for time_prof in sorted(times_list):
            self.print_time_entry(time_prof)

        self.print_time_footer()

        # output the table of uses
        self.print_use_header()

        stuff_to_find = [(stash.IS_STASH_USAGE_NL, None, None),
                         (stash.IS_STASH_STREAM_NL, None, None)]
        messages, temp_config = stash.filter_on_match(stuff_to_find,
                                                      stash_config)

        uses_list = get_stash_uses_list(temp_config)

        for use in sorted(uses_list):
            self.print_use_entry(use)

        self.print_use_footer()

        return config, self.reports

    def print_streq_header(self):
        print (self.streq_header_format_string.format(
                                               "STASH Request Profiles :"))
        print (self.streq_format_string.format("Section", "Item", "Name",
                                               "Domain Profile", "Time Profile",
                                               "Use", "Package", "Included",
                                               "DomainProfile", "TimeProfile",
                                               "UsageProfile"))

    def print_streq_entry(self, stash_req):
        """print the contents of a STASH request to a single line"""
        print (self.streq_format_string.format(stash_req[0],
                                               stash_req[1],
                                               stash_req[2],
                                               stash_req[3],
                                               stash_req[4],
                                               stash_req[5],
                                               stash_req[6],
                                               stash_req[7],
                                            stash_req[3].translate(None, " "),
                                            stash_req[4].translate(None, " "),
                                            stash_req[5].translate(None, " ")))

    def print_streq_footer(self):
        print (self.streq_footer_format_string.format("\n"))

    def print_domain_header(self):
        print (self.domain_header_format_string.format("Domain Profiles :",
                                                      "DomainProfile"))
        print (self.domain_format_string.format("Profile Name", "Levels",
                                                "Area", "Masking", "Meaning",
                                                "Weighting",
                                                "Time Series Domains",
                                                "Included", "ProfileName"))

    def print_domain_entry(self, domain):
        """print the contents of a STASH domain profile to a single line"""
        print (self.domain_format_string.format(domain[0], domain[1],
                                                domain[2], domain[3],
                                                domain[4], domain[5],
                                                domain[6], domain[7],
                                               domain[0].translate(None, " ")))

    def print_domain_footer(self):
        print (self.domain_footer_format_string.format("\n"))

    def print_time_header(self):
        print (self.time_header_format_string.format("Time Profiles :",
                                                     "TimeProfile"))
        print (self.time_format_string.format("Profile Name", "Type",
                                              "Output intervals", "Sampling",
                                              "Processing period",
                                              "Processing period Start",
                                              "Included", "ProfileName"))

    def print_time_entry(self, time_prof):
        """print the contents of a STASH time profile to a single line"""
        print (self.time_format_string.format(time_prof[0], time_prof[1],
                                              time_prof[2], time_prof[3],
                                              time_prof[4], time_prof[5],
                                              time_prof[6],
                                            time_prof[0].translate(None, " ")))

    def print_time_footer(self):
        print (self.time_footer_format_string.format("\n"))

    def print_use_header(self):
        print (self.use_header_format_string.format("Usage Profiles :",
                                                    "UsageProfile"))
        print (self.use_format_string.format("Profile Name",
                                             "Output Destination",
                                             "TAG/Stream name",
                                             "File / Base Name",
                                             "Reinitialisation",
                                             "Packing", "Reserved Headers",
                                             "Included", "ProfileName"))

    def print_use_entry(self, use):
        """print the contents of a STASH useage profile to a single line"""
        print (self.use_format_string.format(use[0], use[1],
                                             use[2], use[3],
                                             use[4], use[5],
                                             use[6], use[7],
                                             use[0].translate(None, " ")))

    def print_use_footer(self):
        print (self.use_footer_format_string.format("-=" *38 +"-=-\n"))

    def int_keys_of_str_tuple(self, record):
        '''Recieves a record in the form of a tuple of strings.
           The elements are converted to integers, where possible,
           to improve sorting when using the tuple as a key'''
        newlist = list(record)
        for index, element in enumerate(newlist):
            try:
                newlist[index] = int(newlist[index])
            except:
                pass
        return tuple(newlist)
        

class STASHPrint_wiki(STASHPrint):
    """Print out the STASH requests, and domain, time and usage profiles,
       from a job in human readable form. Trac wiki format."""

    streq_format_string = ("|| {0:s} || {1:s} || {2:s} "
                          "|| [#{8:s} {3:s}] "
                          "|| [#{9:s} {4:s}] "
                          "|| [#{10:s} {5:s}] "
                          "|| {6:s} || {7:s} ||")
    streq_header_format_string = "\n== {0:s} ==\n"

    domain_format_string = ("|| [[span(id={8:s}, class=wikianchor,"
                            " title=#{8:s}, {0:s})]] "
                            "|| {1:s} || {2:s} || {3:s} "
                            "|| {4:s} || {5:s} || {6:s} || {7:s} ||")
    domain_header_format_string = "\n== {0:s} [=#{1:s}] ==\n"

    time_format_string = ("|| [[span(id={7:s}, class=wikianchor, title=#{7:s},"
                          " {0:s})]] || {1:s} || {2:s} || {3:s} || {4:s} ||"
                          " {5:s} || {6:s} ||")
    time_header_format_string = "\n== {0:s} [=#{1:s}] ==\n"

    use_format_string = ("|| [[span(id={8:s}, class=wikianchor, title=#{8:s},"
                         " {0:s})]] || {1:s} || {2:s} || {3:s} || {4:s} ||"
                         " {5:20s} || {6:16s} || {7:8s} ||")
    use_header_format_string = "\n== {0:s} [=#{1:s}] ==\n"

    def print_domain_entry(self, domain):
        """print the contents of a STASH domain profile to a single line"""
        print (self.domain_format_string.format(
                                             escape_trac_twiki_link(domain[0]),
                                             domain[1], domain[2],
                                             domain[3], domain[4],
                                             domain[5], domain[6],
                                             domain[7],
                                             domain[0].translate(None, " ")))

    def print_time_entry(self, time_prof):
        """print the contents of a STASH time profile to a single line"""
        print (self.time_format_string.format(
               escape_trac_twiki_link(time_prof[0]), time_prof[1],
               time_prof[2], time_prof[3], time_prof[4], time_prof[5],
               time_prof[6], time_prof[0].translate(None, " ")))

    def print_use_entry(self, use):
        """print the contents of a STASH usage profile to a single line"""
        print (self.use_format_string.format(escape_trac_twiki_link(use[0]),
                                             use[1], use[2],
                                             use[3], use[4],
                                             use[5], use[6],
                                             use[7],
                                             use[0].translate(None, " ")))

    def print_use_footer(self):
        print (self.use_footer_format_string.format("-" *4 + "\n"))


class STASHPrint_html(STASHPrint):
    """Print out the STASH requests, and domain, time and usage profiles,
       from a job in human readable form. Html table format."""

    streq_format_string = ("<tr><td> {0:s} </td><td> {1:s} </td><td> {2:s} "
                           "</td><td> <a href=\"#{8:s}\"> {3:s} </a> "
                           "</td><td> <a href=\"#{9:s}\"> {4:s} </a> "
                           "</td><td> <a href=\"#{10:s}\"> {5:s} </a> "
                           "</td><td> {6:s} </td><td> {7:s} </td></tr>")
    streq_header_format_string = "\n<h1> {0:s} </h1>n"
    domain_format_string = ("<tr><td id=\"{8:s}\"> {0:s} </td><td> {1:s}"
                            " </td><td> {2:s} </td><td> {3:s} </td><td> {4:s}"
                            " </td><td> {5:s} </td><td> {6:s} </td><td> {7:s}"
                            " </td></tr>")
    domain_header_format_string = "\n<h2 id=\"{1:s}\"> {0:s} </h2>\n"
    time_format_string = ("<tr><td id=\"{7:s}\"> {0:s} </td><td> {1:s} "
                          "</td><td> {2:s} </td><td> {3:s} </td><td> {4:s} "
                          "</td><td> {5:s} </td><td> {6:s} </td></tr>")
    time_header_format_string = "\n<h2 id=\"{1:s}\"> {0:s} </h2>\n"
    use_header_format_string = "\n<h2 id=\"{1:s}\"> {0:s} </h2>\n"
    use_format_string = ("<tr><td id=\"{8:s}\"> {0:s} </td><td> {1:s} "
                         "</td><td> {2:s} </td><td> {3:s} </td><td> {4:s} "
                         "</td><td> {5:20s} </td><td> {6:16s} </td><td> "
                         "{7:8s} </td></tr>")

    def print_streq_header(self):
        """print any required pre-amble for the table of STASH requests"""
        print ("<table style=\"width:100% ; border: 5px solid black; "
               "padding: 2px; border-collapse: collapse;\">")
        print ("<style> td, th {border: 1px solid black; padding: 5px; "
               "}</style>")
        print (self.streq_format_string.format("Section", "Item", "Name",
                                              "Domain Profile", "Time Profile",
                                               "Use", "Package", "Included",
                                               "DomainProfile", "TimeProfile",
                                               "UsageProfile"))

    def print_domain_header(self):
        """print any required pre-amble for the table of STASH domain profiles"""
        print (self.domain_header_format_string.format("Domain Profiles :",
                                                       "DomainProfile"))
        print ("<table style=\"width:100% ; border: 5px solid black; "
               "padding: 2px; border-collapse: collapse;\">")
        print ("<style> td, th {border: 1px solid black; padding: 5px; }"
               "</style>")
        print (self.domain_format_string.format("Profile Name", "Levels",
                                                "Area", "Masking", "Meaning",
                                                "Weighting",
                                                "Time Series Domains",
                                                "Included", "ProfileName"))

    def print_time_header(self):
        """print any required pre-amble for the table of STASH time profiles"""
        print (self.time_header_format_string.format("Time Profiles :",
                                                     "TimeProfile"))
        print ("<table style=\"width:100% ; border: 5px solid black; "
               "padding: 2px; border-collapse: collapse;\">")
        print ("<style> td, th {border: 1px solid black; padding: 5px; }"
               "</style>")
        print (self.time_format_string.format("Profile Name", "Type",
                                              "Output intervals", "Sampling",
                                              "Processing period",
                                              "Processing period Start",
                                              "Included", "ProfileName"))

    def print_use_header(self):
        """print any required pre-amble for the table of STASH usage profiles"""
        print (self.use_header_format_string.format("Usage Profiles :",
                                                    "UsageProfile"))
        print ("<table style=\"width:100% ; border: 5px solid black; "
               "padding: 2px; border-collapse: collapse;\">")
        print ("<style> td, th {border: 1px solid black; padding: 5px; }"
               "</style>")
        print (self.use_format_string.format("Profile Name",
                                             "Output Destination",
                                             "TAG/Stream name",
                                             "File / Base Name",
                                             "Reinitialisation",
                                             "Packing",
                                             "Reserved Headers",
                                             "Included",
                                             "ProfileName"))

    def print_streq_footer(self):
        print"</table>\n"

    def print_domain_footer(self):
        print"</table>\n"

    def print_time_footer(self):
        print"</table>\n"

    def print_use_footer(self):
        print"</table>\n<p><hr></p>\n"


def get_stash_reqs_list(config):
    """Take a nested config node object and return a list of tuples containing
       the elements of a STASH request namelist"""
    # Find the STASHmaster and get the nested dictionary of
    # STASHmaster records.
    parser = widget.stash_parse.StashMasterParserv1(
                                             widget.stash.STASHMASTER_PATH)
    lookup_dict = parser.get_lookup_dict()

    stash_list = []

    for node_key, node in config.walk(no_ignore=False):
        if not isinstance(node.value, dict):
            continue

        if node.state is "":
            included = "Yes"
        else:
            included = stash._INCLUDED_DICT[node.state]

        isec = get_item_value(node, "isec")
        item = get_item_value(node, "item")
        dom_name = get_item_value(node, "dom_name")
        tim_name = get_item_value(node, "tim_name")
        use_name = get_item_value(node, "use_name")
        package = get_item_value(node, "package")
        if isec == "! missing !":
            isec = "-1"
        if item == "! missing !":
            item = "-1"

        try:
            stash_name = lookup_dict[isec][item]["name"]
        except:
            stash_name = 'Unknown STASH item'
        if isec == "-1" and item == "-1":
            stash_name = 'Error with namelist : ' + node_key[0]

        try:
            stash_list.append((isec, item, stash_name, dom_name, tim_name,
                              use_name, package, included))
        except:
            print "Error trying to handle STASH Request data from node:"
            stash.debug_print_node(node, node_key, "get_stash_reqs_list")
            raise

    return stash_list


def get_stash_domains_list(config):
    """Take a nested config node object and return a list of tuples containing
       the elements of a STASH domain profile namelist"""

    _level_type_codes = {
        "1": "Model rho levels",
        "2": "Model theta levels",
        "3": "Pressure levels",
        "4": "Geometric height levels",
        "5": "Single level",
        "6": "Deep soil levels",
        "7": "Potential temperature levels",
        "8": "Potential vorticity levels",
        "9": "Cloud threshold levels",
        '! missing !': "! Undefined !"}
    _pseudo_level_codes = {
        "0": "None",
        "1": "SW radiation bands",
        "2": "LW radiation bands",
        "3": "Atmospheric assimilation groups",
        "8": "HadCM2 Sulphate Loading Pattern Index",
        "9": "Land and Vegetation Surface Types",
        "10": "Sea ice categories",
        "11": "Number of land surface tiles x maximum number of snow layers",
        "12": ("COSP pseudo level categories for satellite observation "
               "simulator project"),
        "13": ("COSP pseudo level categories for satellite observation "
               "simulator project"),
        "14": ("COSP pseudo level categories for satellite observation "
               "simulator project"),
        "15": ("COSP pseudo level categories for satellite observation "
               "simulator project"),
        "16": ("COSP pseudo level categories for satellite observation "
               "simulator project"),
        '! missing !': "! Undefined !"}
    _horiz_dom_codes = {
        "1": "Global",
        "2": "N hemisphere",
        "3": "S hemisphere",
        "4": "30-90 N",
        "5": "30-90 S",
        "6": "0-30 N",
        "7": "0-30 S",
        "8": "30S-30N",
        "9": "Area specified in degrees",
        "10": "Area specified in gridpoints",
        '! missing !': "! Undefined !"}
    _gridpoint_codes = {
        "1": "All points",
        "2": "Land points",
        "3": "Sea points",
        "4": "Full use of non-MDI gridpoint data in max/min time process",
        '': "Unknown",
        '! missing !': "! Undefined !"}
    _spatial_mean_codes = {
        "0": "None",
        "1": "Vertical",
        "2": "Zonal",
        "3": "Meridional",
        "4": "Horizontal area",
        '': "Unknown",
        '! missing !': "! Undefined !"}
    _weighting_codes = {
        "0": "None",
        "1": "Horizontal",
        "2": "Volume",
        "3": "Mass",
        '! missing !': "! Undefined !",
        '': "Unknown"}

    domain_list = []

    for node_key, node in config.walk(no_ignore=False):
        # Skip top level info, looking only for config nodes (dictionaries)
        if not isinstance(node.value, dict):
            continue

        if node.state is "":
            included = "Yes"
        else:
            included = stash._INCLUDED_DICT[node.state]

        try:
            dom_name = get_item_value(node, "dom_name")
            iest = get_item_value(node, "iest")
            ilevs = get_item_value(node, "ilevs")
            imn = get_item_value(node, "imn")
            imsk = get_item_value(node, "imsk")
            inth = get_item_value(node, "inth")
            iopa = get_item_value(node, "iopa")
            iopl = get_item_value(node, "iopl")
            isth = get_item_value(node, "isth")
            iwst = get_item_value(node, "iwst")
            iwt = get_item_value(node, "iwt")
            levb = get_item_value(node, "levb")
            levlst = get_item_value(node, "levlst")
            levt = get_item_value(node, "levt")
            plt = get_item_value(node, "plt")
            pslist = get_item_value(node, "pslist")
            rlevlst = get_item_value(node, "rlevlst")
            tblim = get_item_value(node, "tblim")
            tblimr = get_item_value(node, "tblimr")
            telim = get_item_value(node, "telim")
            tnlim = get_item_value(node, "tnlim")
            ts = get_item_value(node, "ts")
            tslim = get_item_value(node, "tslim")
            tsnum = get_item_value(node, "tsnum")
            ttlim = get_item_value(node, "ttlim")
            ttlimr = get_item_value(node, "ttlimr")
            twlim = get_item_value(node, "twlim")
        except:
            print "Error trying to handle Domain data from node:"
            stash.debug_print_node(node, node_key, "get_stash_domains_list")
            raise

        # Logic below only becomes remotely clear if looking at
        # STASH control file appendix in UMDP C4

        # ascertain level types and coverage :
        level_coverage = _level_type_codes[iopl]
        if iopl in "1 2 6".split():
            if ilevs == "1":
                level_coverage = (level_coverage +
                    ". Contiguous range. From {0:s} to {1:s}.".format(levb,
                                                                      levt))
            elif ilevs == "2":
                level_coverage = (level_coverage +
                    "List: {0:s}".format(", ".join(levlst.split(","))))
        elif iopl == "3":
            level_coverage = (level_coverage +
                " : {0:s}".format(", ".join(rlevlst.split(","))))
        elif plt in "1 2 3 8 9 10 11 12 13 14 15 16".split():
            level_coverage = (level_coverage +
                ". {0:s} ( {1:s} )".format(_pseudo_level_codes[plt],
                                           ", ".join(pslist.split(","))))
        # ascertain Area:
        if iopa in _horiz_dom_codes.keys():
            area_coverage = _horiz_dom_codes[iopa]
        else:
            area_coverage = "Unknown"

        if iopa in "9 10".split():
            area_coverage = (area_coverage +
                " ( {0:s} N, {1:s} S, {2:s} W, {3:s} E )".format(inth, isth,
                                                                 iwst, iest))
        # ascertain Grid Points Masking option:
        gridpoint_masking = _gridpoint_codes[imsk]
        # ascertain Spatial Meaning:
        spatial_meaning = _spatial_mean_codes[imn]
        # ascertain Weighting Option:
        weighting = _weighting_codes[iwt]
        # ascertain Time Series Domains:
        if ts == "Y":
            if 'ttlim' in self.attributes:
                top = self.attributes['ttlim']
            else:
                top = self.attributes['ttlimr']
            if 'tblim' in self.attributes:
                bot = self.attributes['tblim']
            else:
                bot = self.attributes['tblimr']
            time_series_domains = ("{0:s} time series domains. Horizontal "
                                   "limits: {1:s} N, {2:s} S, {3:s} E, {4:s} "
                                   "W. Vertical limits {5:s} - "
                                   "{6:s}".format(tsnum, tnlim, tslim, telim,
                                                  twlim, bot, top))
        else:
            time_series_domains = "No Time Series Domains"

        domain_list.append((dom_name,
                            level_coverage,
                            area_coverage,
                            gridpoint_masking,
                            spatial_meaning,
                            weighting,
                            time_series_domains,
                            included))

    return domain_list


def get_stash_times_list(config):
    """Take a nested config node object and return a list of tuples containing
       the elements of a STASH time profile namelist"""
    _time_processing_codes = {'0': "Not required by STASH, but space required.",
                              '1': "Replace",
                              '2': "Accumulate",
                              '3': "Time mean.",
                              '4': "Append time-series",
                              '5': "Maximum",
                              '6': "Minimum",
                              '7': "Trajectories",
                              '! missing !': "! Undefined !"}
    _unit_conv = {'1': "timesteps",
                  '2': "hours",
                  '3': "days",
                  '4': "dump periods",
                  '5': "minutes",
                  '6': "seconds",
                  '! missing !': "! Undefined !"}
    time_list = []
    for node_key, node in config.walk(no_ignore=False):
        # Skip top level info, looking only for config nodes (dictionaries)
        if not isinstance(node.value, dict):
            continue
        if node.state is "":
            included = "Yes"
        else:
            included = stash._INCLUDED_DICT[node.state]

        try:
            tim_name = get_item_value(node, "tim_name")
            ityp = get_item_value(node, "ityp")
            intv = get_item_value(node, "intv")
            iser = get_item_value(node, "iser")
            isam = get_item_value(node, "isam")
            isdt = get_item_value(node, "isdt")
            itimes = get_item_value(node, "itimes")
            iedt = get_item_value(node, "iedt")
            ioff = get_item_value(node, "ioff")
            ifre = get_item_value(node, "ifre")
            istr = get_item_value(node, "istr")
            iopt = get_item_value(node, "iopt")
            iend = get_item_value(node, "iend")
            unt1 = get_item_value(node, "unt1")
            unt2 = get_item_value(node, "unt2")
            unt3 = get_item_value(node, "unt3")
        except:
            print "Error trying to handle Domain data from node:"
            stash.debug_print_node(node, node_key, "get_stash_times_list")
            raise
        time_processing_type = _time_processing_codes[ityp]
        time_output_intervals = time_sampling = "--"
        time_processing_period = time_processing_start = "--"
        if ityp in "2 3 4 5 6 7".split():
            if 'intv' is not None:
                value = "all" if intv == "-1" else intv
                time_processing_period = (
                    "{0:s} {1:s}".format(value, _unit_conv[unt1]))
                time_processing_start = (
                    "{0:s} {1:s}".format(ioff, _unit_conv[unt1]))
            time_sampling = "{0:s} {1:s}".format(isam, _unit_conv[unt2])
            if iopt == "1":
                time_output_intervals = (
                    "Regular output times ({3:s}). Start = {0:s}. "
                    "End = {1:s}. Frequency = {2:s}.".format(istr, iend,
                                                             ifre,
                                                             _unit_conv[unt3]))
            elif iopt == "2":
                time_output_intervals = ("List of times "
                                         "({0:s})= {1:s}".format(
                                             _unit_conv[unt3], iser))
            elif iopt == "3":
                time_output_intervals = ("Date range. From {0:s} to "
                                         "{1:s}".format(isdt, iedt))
        time_list.append((tim_name, time_processing_type,
                          time_output_intervals, time_sampling,
                          time_processing_period, time_processing_start,
                          included))

    return time_list


def get_stash_uses_list(config):
    """Take a nested config node object and return a list of tuples containing
       the elements of a STASH usage profile namelist combined with the
       associated elements from the streams namelist as well"""

    _output_dest_codes = {'1': "Dump store with user specified tag",
                          '2': "Dump store with climate mean tag",
                          '3': "Write to output stream",
                          '5': "Mean diagnostic direct to mean fieldsfile",
                          '6': "Secondary dump store with user tag",
                          '! missing !': "! Undefined !"}
    _unit_conv = {'0': "None",
                  '1': "Hours",
                  '2': "Days",
                  '3': "Timesteps",
                  '4': "Real Months",
                  '! missing !': "! Undefined !"}
    _packing_types = {'0': "No packing",
                      '1': "Operational packing",
                      '2': "Standard Climate packing",
                      '4': "Stratosphere packing",
                      '5': "New Climate packing",
                      '6': "Simple GRIB packing",
                      '! missing !': "! Undefined !"}
    use_list = []
    stream = {'macro': {"filename": "None", "reinit": "--",
                        "packing": "--", "reserved_headers": "--"}}

    stuff_to_find = [(stash.IS_STASH_STREAM_NL, None, None)]
    messages, temp_config = stash.filter_on_match(stuff_to_find, config)

    # Step 1 : Get the stream information.
    for node_key, node in temp_config.walk(no_ignore=False):
        # Skip top level info, looking only for config nodes (dictionaries)
        if not isinstance(node.value, dict):
            continue
        try:
            stream_name = get_item_value(node, "file_id")

            packing = get_item_value(node, "packing")
            resvd_hdrs = get_item_value(node, "reserved_headers")
            l_reinit = get_item_value(node, "l_reinit")
            reinit_unit = get_item_value(node, "reinit_unit")
            reinit_start = get_item_value(node, "reinit_start")
            reinit_end = get_item_value(node, "reinit_end")
            reinit_step = get_item_value(node, "reinit_step")
            filename = get_item_value(node, "filename")
            filename_base = get_item_value(node, "filename_base")

            if l_reinit == ".true.":
                filename = filename_base
                reinit = "Periodic reinitialisation in {0:s}.".format(
                             _unit_conv[reinit_unit])
                reinit += " Start = {0:s}.".format(reinit_start)
                reinit += " End = {0:s}.".format(reinit_end)
                reinit += " Step = {0:s}.".format(reinit_step)
            else:
                reinit = "No periodic reinitialisation"

            stream[stream_name] = {}

            stream[stream_name]["packing"] = _packing_types[packing]
            stream[stream_name]["reserved_headers"] = resvd_hdrs
            stream[stream_name]["filename"] = filename
            stream[stream_name]["reinit"] = reinit
        except:
            print "Error trying to handle Stream data from node:"
            stash.debug_print_node(node, node_key, "get_stash_uses_list")
            raise

    # Step 2 : Get the Use profile.
    stuff_to_find = [(stash.IS_STASH_USAGE_NL, None, None)]
    messages, temp_config = stash.filter_on_match(stuff_to_find, config)

    for node_key, node in temp_config.walk(no_ignore=False):
        # Skip top level info, looking only for config nodes (dictionaries)
        if not isinstance(node.value, dict):
            continue

        if node.state is not "":
            included = stash._INCLUDED_DICT[node.state]
        else:
            included = "Yes"

        try:
            use_name = get_item_value(node, "use_name")
            locn = get_item_value(node, "locn")
            macrotag = get_item_value(node, "macrotag")
            file_id = get_item_value(node, "file_id")

            output_destination = _output_dest_codes[locn]
            output_dest = "--"
            temp_file_id = 'macro'
            if locn in "1 2 6".split():
                output_dest = "Tag = " + macrotag
            elif locn in "3".split():
                temp_file_id = file_id
                output_dest = "File ID = " + file_id
            else:
                output_dest = "! Undefined !"

            use_list.append((use_name,
                             output_destination,
                             output_dest,
                             stream[temp_file_id]["filename"],
                             stream[temp_file_id]["reinit"],
                             stream[temp_file_id]["packing"],
                             stream[temp_file_id]["reserved_headers"],
                             included))
        except:
            print "Error trying to handle Stream data from node:"
            stash.debug_print_node(node, node_key, "get_stash_uses_list")
            raise

    return use_list


def escape_trac_twiki_link(text):
    """Escape recognised CamelCase words"""
    regex = r'[A-Z][a-z]+([A-Z][a-z]+)+$'
    if re.match(regex, text):
        safe_text = "!" + text
    else:
        safe_text = text
    return safe_text


def get_item_value(node, key):
    """Get the value for a given key in a config node object providing a
       safe value if the rose-app config file is malformed"""
    try:
        value = node.get([key]).value.strip(" '")
    except:
        value = "! missing !"
    return value
