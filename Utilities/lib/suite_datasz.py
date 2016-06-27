#! /usr/bin/env python
"""
 *****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
 *****************************COPYRIGHT******************************

 Code Owner:  Irina Linova-Pavlova
 Name:        suite_datasz.py
 Description: Calculates size of suite output for one year
"""

# Module imports
import datetime
import os.path
import sys
sys.path.append("/home/h03/fcm/rose/lib/python")
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

        with open(stashmaster_filename, 'r') as fp_stash:
            lines = fp_stash.readlines()

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


class Exppxi(object):
    """Extract STASHmaster data."""

    def __init__(self, stash_lookup):
        self.stash_lookup = stash_lookup

    def get(self, isec, item, element_name):
        """Return a STASHmaster record field value, called by name.
        For example, calling:
        get(0, 1, "space")
        will return the space code for the STASHmaster record
        for section 0, item 1.
        """
        return self.stash_lookup[isec][item][element_name]


class ConfigItemNotFoundError(KeyError):
    """Report a missing configuration item."""

    ERROR_MISSING = "Cannot find configuration setting: {0}"

    def __str__(self):
        if len(self.args) > 1:
            id_ = self.args[0] + "=" + self.args[1]
        else:
            id_ = self.args[0]

        return self.ERROR_MISSING.format(id_)


def _get_var(config, section, option, default=None, array=False,
             type_=None):
    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Get a namelist variable value from the config
    Input:
        config - um job configuration content
        section - namelist:actual_name
        option - variable name
        default - default value
        array - True, False for scalars
        type - one of (integer, real, character, logical)
    Returns:
        value of requested variable
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
    node = config.get([section, option], no_ignore=True)
    if node is None:
        if default is None:
            raise ConfigItemNotFoundError(section, option)
        return default
    if array:
        return convert_type(rose.variable.array_split(node.value), type_)
    return convert_type(node.value, type_)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def convert_type(value, type_):
    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Cast based on Fortran types
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
    if isinstance(value, list):
        for i, val in enumerate(value):
            value[i] = convert_type(val, type_)
        return value
    if type_ == "integer":
        return int(value)
    if type_ in ["real", "double precision"]:
        return float(value)
    if type_ in ["logical"]:
        return value.lower() == ".true."
    if type_ == "character":
        return value.strip("'")


def lst_str2num(lst_str, conv_type):
    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Input:
        lst_str - list of string
    Returns:
        lst_num - list of numbers
        if length is 0, empty list
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    lst_num = []

    for ind, s_elm in enumerate(lst_str):
        if conv_type == "i":
            lst_num.append(int(s_elm))
        elif conv_type == "r":
            lst_num.append(float(s_elm))

    return lst_num


def create_com_dict(config):
    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Input:
        config - job name lists
    Returns:
        information in form 'key': value:
        * 'stpp' - steps per period
        * 'sepp' = length of period in seconds
        * 'dfst' - dump frequency in steps
        * 'meanfreq' - meaning periods, integer coefficients
        * 'meanprds' - mean periods
        * 'gl_rowlen' - global row length
        * 'gl_rows' - global rows
        * 'l_endgame' - indicates theta or UV grid for global_rows
        * 'river_rowlen' - river row length
        * 'river_rows' - river rows
        * 'job_prd' - run for period [years, months, days]
        * 'l_mean_seq' - meaning requested
        * 'um_sect_sz' - um_sector_size for data blocks
        * 'len_days'- run perios in days
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    entries = {}
    zero_prd = [0, 0, 0, 0]
    mean_file = ["None", "None", "None", "None"]

    entries['stpp'] = _get_var(config, "namelist:nlstcgen",
                               "steps_per_periodim", type_="integer")

    entries['sepp'] = _get_var(config, "namelist:nlstcgen",
                               "secs_per_periodim", type_="integer")

    day_sec = 86400.0
    stpp = entries['stpp']        # time steps for period
    sepp = entries['sepp']        # period in sec, 1 day but could be any
    stpd = stpp * day_sec / sepp  # time steps per day
    days = sepp / day_sec
    entries['stpd'] = int(stpd)

    dump_freq = _get_var(config, "namelist:nlstcgen",
                         "dumpfreqim", type_="integer")

    dump_unit = _get_var(config, "namelist:nlstcgen",
                         "dump_frequency_units", type_="integer")

    if dump_unit == 3:
        # time steps
        dfst = dump_freq
    elif dump_unit == 2:
        # days
        dfst = (stpp * dump_freq) / days
    elif dump_unit == 1:
        # hours
        dfst = (stpp * dump_freq) / (days * 24)
    entries['dfst'] = dfst

    entries['l_mean_seq'] = _get_var(config, "namelist:nlstcgen",
                                     "l_meaning_sequence", type_="logical")
    if entries['l_mean_seq']:
        entries['ppselectim'] = lst_str2num((_get_var(config,
                                            "namelist:nlstcgen",
                                            "ppselectim",
                                            type_="character")).rsplit(","),
                                            "i")

        entries['meanfreq'] = lst_str2num((_get_var(config,
                                          "namelist:nlstcgen", "meanfreqim",
                                          type_="character")).rsplit(","),
                                          "i")

        if entries['ppselectim'][0] > 0:
            flnm_1 = _get_var(config, "namelist:nlstcgen",
                              "mean_1_filename_base", type_="character")
            mean_file[0] = flnm_1

        if entries['ppselectim'][1] > 0:
            flnm_2 = _get_var(config, "namelist:nlstcgen",
                              "mean_2_filename_base", type_="character")
            mean_file[1] = flnm_2
        if entries['ppselectim'][2] > 0:
            flnm_3 = _get_var(config, "namelist:nlstcgen",
                              "mean_3_filename_base", type_="character")
            mean_file[2] = flnm_3
        if entries['ppselectim'][3] > 0:
            flnm_4 = _get_var(config, "namelist:nlstcgen",
                              "mean_4_filename_base", type_="character")
            mean_file[3] = flnm_4

    else:
        entries['ppselectim'] = zero_prd
        entries['meanfreq'] = zero_prd

    entries['mean_file'] = mean_file
    lst_mnp = []
    v1_prd = entries['ppselectim']
    v2_prd = entries['meanfreq']
    mnk = entries['dfst'] / entries['stpp']
    mnp_n = int(mnk * v1_prd[0] * v2_prd[0])
    lst_mnp.append(mnp_n)
    for i in range(1, 4):
        mnp_n = mnp_n * v1_prd[i] * v2_prd[i]
        lst_mnp.append(mnp_n)
    entries['meanprds'] = lst_mnp

    # River_rowlen and river_rows have fixed UM values
    entries['river_rowlen'] = 360
    entries['river_rows'] = 180

    # Get grid sizes
    entries['l_endgame'] = _get_var(config, "namelist:run_dyn",
                                    "l_endgame", type_="logical")

    entries['gl_rowlen'] = _get_var(config, "namelist:nlsizes",
                                    "global_row_length", type_="integer")

    entries['gl_rows'] = _get_var(config, "namelist:nlsizes",
                                  "global_rows", type_="integer")

    j_lst = [10, 0, 0, 0, 0, 0]
    len_in_days = int(j_lst[0]) * 360 + int(j_lst[1]) * 30 + int(j_lst[2])
    entries['len_days'] = len_in_days

    # Use default value for UM_SECTOR_SIZE (UM var io_field_padding) 512
    entries['um_sect_sz'] = 512

    return entries


def usage_prof_desc(config):
    """
    Returns a  dictionary of usage profile in form:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key  - name of profile
    item - dictionary created from config
           {'locn'      - type of destination
            'file_id'   - eg. 'pp7'
            'macrotag'  - for meaning files only
            'stream_n'  - stream number
            'stream_id' - name list for stream eg. namelist:nlstcall_pp(pp9)
            'nml_id'    - namelist of usage profile eg.'namelist:use(458d84c1)'
            'ft_step'   - file re-initialization step
            'reinit_un' - reinit unit
            'res_hdrs'  - reserved headers
            'data_start'- position of data start in fields file
            'hdr_nodata'- size of header with no data in file
            'max_pp_num'- max file number used
            'pp_file_lst' - list of pp files
            'mean_tag_lst' - list of mean tags
           }
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    entries = {}
    max_file_n = -1
    max_mean_n = -1
    stream_lst = []
    macrotag_lst = []
    unit_names = ['none', 'hour', 'day', 'time step', 'real month']
    data_pos = 524288
    default_res_hdrs = 4096
    fix_hdr = 1028

    for section, sect_node in config.value.items():
        if (not section.startswith("namelist:use(") or
            sect_node.is_ignored()):

            # Pass section
            continue

        locn = _get_var(config, section,
                        "locn", type_="integer")
        if locn == 3:
            file_id = _get_var(config, section, "file_id", type_="character")
            stream_id = "namelist:nlstcall_pp("+file_id+")"
            macrotag = ''
            sect_node = config.get([stream_id])
            ft_step = int(sect_node['reinit_step'].value)
            reinit_un = int(sect_node['reinit_unit'].value)
            res_hdrs = int(sect_node['reserved_headers'].value)
            stream_n = int(file_id.lstrip("pp"))

            if stream_n > max_file_n:
                max_file_n = stream_n
            stream_lst.append(stream_n)

        elif locn == 2:
            file_id = ''
            stream_id = ''
            macrotag = _get_var(config, section, "macrotag", type_="integer")
            reinit_un = res_hdrs = ft_step = 0
            stream_n = int(macrotag)
            if stream_n > max_mean_n:
                max_mean_n = stream_n
            macrotag_lst.append(stream_n)

        if locn == 2 or locn == 3:
            use_name = _get_var(config, section, "use_name", type_="character")
            nml_id = section
            res_hdrs = max(res_hdrs, default_res_hdrs)
            descriptor_sz = (fix_hdr + res_hdrs * 64) * 8
            dv_res = divmod(descriptor_sz, data_pos)
            dec = dv_res[0] + 1
            d_temp = (dec * data_pos) / 8
            data_start = max(d_temp, data_pos)

            wrk_dict = {}
            wrk_dict = {'locn': locn, 'file_id': file_id,
                        'macrotag': macrotag,
                        'stream_n': stream_n, 'stream_id': stream_id,
                        'nml_id': nml_id, 'ft_step': ft_step,
                        'reinit_un': unit_names[reinit_un],
                        'res_hdrs': res_hdrs, 'data_start': data_start,
                        'hdr_nodata': descriptor_sz / 8}
            entries[use_name] = wrk_dict

    # Add lists and max number
    entries['max_pp_num'] = max_file_n
    entries['pp_file_lst'] = stream_lst
    entries['mean_tag_lst'] = macrotag_lst

    return entries


def form_request_keys(config, lst_keys):
    """
    Returns a dictionary of requested items with keys :
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key  -  primary key formed from section, item,
            domain, time, usage profile name joined by '_'
            for example:  5_285_DIAG_TDMPMN_UPMEAN
    value - dictionary initially with namelist id and after
            extended with vertical levels, horizontal area etc.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    entries = {}
    second_keys = {}

    for section, sect_node in config.value.items():
        if (not section.startswith("namelist:streq(") or
                sect_node.is_ignored()):
            continue

        use_str = _get_var(config, section,
                           "use_name", type_="character")
        if use_str in lst_keys:
            sec_str = _get_var(config, section,
                               "isec", type_="character")
            item_str = _get_var(config, section,
                                "item", type_="character")
            dom_str = _get_var(config, section,
                               "dom_name", type_="character")
            tim_str = _get_var(config, section,
                               "tim_name", type_="character")
            key_req = (sec_str + '_' + item_str + '_' +
                       dom_str + '_' + tim_str + '_' + use_str)
            second_keys = {'nml_streq': section, 'sdom': dom_str,
                           'stim': tim_str, 'suse': use_str}
            entries[key_req] = second_keys

    return entries


def create_prof_dict(config, profile_nmlist, var_name, lst_keys):
    """
    Returns dictionary profile in a form:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key  - name of profile
    item - namelist_id
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    entries = {}
    for section, sect_node in config.value.items():
        if (not section.startswith(profile_nmlist) or
                sect_node.is_ignored()):
            continue
        profile_name = _get_var(config, section,
                                var_name, type_="character")
        if profile_name in lst_keys:
            entries[profile_name] = section

    return entries


def inactive(dict_passed, field):
    """
    Check state of the field in rose config file
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Returns: 0 - active
             1 - inactive
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    tmp_dict = {}
    ret_code = 1
    str_state = "'state': ''"

    if field in dict_passed.keys():
        tmp_dict = dict_passed[field]
        str_tmp = str(tmp_dict)
        if str_state in str_tmp:
            ret_code = 0
    return ret_code


def add_vlevels(i_dict, d_dict, config):
    """
    Adds number of veritical levels to the item dictionary :
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key  - 'vlevs'
    item - integer taken from domain profile decription
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    for tmp_key, tmp_val in d_dict.iteritems():

        tmp_dict = {}
        tmp_dict = config[tmp_val].value
        iopl = _get_var(config, tmp_val, "iopl", type_="integer")
        rc_act = inactive(tmp_dict, 'iopl')

        nlevs = 0
        if not rc_act:
            # Single or unspecified levels
            if iopl == 5:
                nlevs = 1
                if not inactive(tmp_dict, 'pslist'):
                    pslist = lst_str2num((_get_var(config, tmp_val, "pslist",
                                          type_="character")).rsplit(","), "i")

                    if isinstance(pslist, list):
                        nlevs = len(pslist)

            # Model rho or theta levels
            elif iopl == 1 or iopl == 2 and not inactive(tmp_dict, 'imn'):
                vert_mean = 0
                vert_mean = _get_var(config, tmp_val, "imn", type_="integer")
                if not inactive(tmp_dict, 'levlst'):
                    levlst = lst_str2num((_get_var(config, tmp_val, "levlst",
                                         type_="character")).rsplit(","), "i")
                    if isinstance(levlst, list):
                        nlevs = len(levlst)
                    else:
                        nlevs = 1
                elif vert_mean == '1':
                    nlevs = 1
                else:
                    lev_t = _get_var(config, tmp_val, "levt", type_="integer")
                    lev_b = _get_var(config, tmp_val, "levb", type_="integer")
                    nlevs = lev_t - lev_b + 1

            # Pressure, geometric height, constant theta surfaces, potential
            # vorticity or cloud threshold levels
            elif (iopl == 3 or iopl == 4 or iopl == 7 or
                  iopl == 8 or iopl == 9 and
                  not inactive(tmp_dict, 'rlevlst')):
                nlevs = 1
                rlevlst = lst_str2num((_get_var(config, tmp_val, "rlevlst",
                                       type_="character")).rsplit(","), "r")

                if isinstance(rlevlst, list):
                    nlevs = len(rlevlst)

            # Deep soil levels
            elif iopl == 6 and not inactive(tmp_dict, 'levt'):
                nlevs = _get_var(config, tmp_val, "levt", type_="integer")

            # Now add vertical levels to each request with that domain name
            for item_key in i_dict.keys():
                tmp2_dict = i_dict[item_key]
                if tmp2_dict['sdom'] == tmp_key:
                    vlev_upd = {'vlevs': nlevs}
                    i_dict[item_key].update(vlev_upd)

    return i_dict


def add_horiz_area(i_dict, d_dict, config):
    """
    Gathers information to refine the horizontal area.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    i_dict - item dictionary
    d_dict - domain dictionary
    Returns: div_x, div_y, imn - coeficients to calculate
             matrix dimention
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    for tmp_key, tmp_val in d_dict.iteritems():

        iopa = _get_var(config, tmp_val, "iopa", type_="integer")
        imn = _get_var(config, tmp_val, "imn", type_="integer")

        if iopa == 1:
            cf_x = cf_y = 1
        elif iopa == 2 or iopa == 3:
            cf_x = 1
            cf_y = 2
        elif iopa == 4 or iopa == 5 or iopa == 8:
            cf_x = 1
            cf_y = 3
        elif iopa == 6 or iopa == 7:
            cf_x = 1
            cf_y = 6
        elif iopa == 9 or iopa == 10:
            # Limited area do not consider for now
            cf_x = cf_y = 1
        else:
            # for future options
            cf_x = cf_y = 1

        # Now add horizontal points to all requests with that domain name
        for item_key in i_dict.keys():
            tmp2_dict = i_dict[item_key]
            if tmp2_dict['sdom'] == tmp_key:
                horiz_area = {'div_x': cf_x, 'div_y': cf_y, 'imean': imn}
                i_dict[item_key].update(horiz_area)

    return i_dict


def add_outfreq(i_dict, t_dict, com_dict, config):
    """
    Adds to the item dictionary output frequency (per day):
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    i_dict - items dictionary
    t_dict - time profiles dictionary
    com_dict - dictionary with common info
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    day_sec = 86400
    stpp = com_dict['stpp']       # time steps for period
    sepp = com_dict['sepp']       # period in sec
    dfst = com_dict['dfst']       # dumps in time steps
    stpd = stpp * day_sec / sepp  # time steps per day

    for tmp_key, tmp_val in t_dict.iteritems():

        iopt = _get_var(config, tmp_val, "iopt", type_="integer")

        if iopt == 1 or iopt == 3:
            # Regular intervals
            unt3 = _get_var(config, tmp_val, "unt3", type_="integer")
            ifre = _get_var(config, tmp_val, "ifre", type_="integer")
            # time step (1) hours (2) days (3) dump preriods (4)
            if unt3 == 1:
                dfre = stpd
            elif unt3 == 2:
                dfre = 24.0 / ifre
            elif unt3 == 3:
                dfre = 1.0 / ifre
            elif unt3 == 4:
                dfre = 1.0 * (day_sec * stpp) / (dfst * sepp)
            else:
                dfre = 0

            if iopt == 3:
                # Add start/stop period
                isdt = lst_str2num((_get_var(config, tmp_val, "isdt",
                                   type_="character")).rsplit(","), "i")
                iedt = lst_str2num((_get_var(config, tmp_val, "iedt",
                                   type_="character")).rsplit(","), "i")
        else:
            # iopt = 2 not considered at the moment
            dfre = 0.0

        # Add output frequency to each request with that time profile
        for item_key in i_dict.keys():
            tmp2_dict = i_dict[item_key]
            if tmp2_dict['stim'] == tmp_key:
                dfre_upd = {'kfreq': dfre, 'iopt': iopt}
                i_dict[item_key].update(dfre_upd)
                if iopt == 3:
                    prd_upd = {'isdt': isdt, 'iedt': iedt}
                    i_dict[item_key].update(prd_upd)
    return i_dict


def fill_stash_dict(item_dict, exppxi):
    """
    Fills stash dictionary from STASHmaster file:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key   - section_item, for example "01_003"
    value - dictionary gathered from stash record
           {'grid': 1,
            'pkgcode': "-3   -3   -3   -3  -12   20  -99  -99  -99  -99"}
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
    stash_dict = {}

    for tmp_key in item_dict.keys():

        tmp_list = tmp_key.rsplit("_")
        isec = tmp_list[0]
        item = tmp_list[1]
        grid = exppxi.get(isec, item, "grid")
        pkgcode_str = exppxi.get(isec, item, "pc1-a")
        pkgcode_lst = pkgcode_str.split()
        pkgcode = pkgcode_lst[4]

        isec = isec.rjust(2, "0")
        item = item.rjust(3, "0")
        stash_key = "1_" + isec + "_" + item
        stash_dict[stash_key] = {'grid': grid, 'pkgcode': pkgcode}

    return stash_dict


def fill_ratio_dict(db_ratio_flnm, stash_dict):
    """
    Fills ratio dictionary from DB ratio file
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    key  - model_section_item, for example "1_01_003"
    item - dictionary gathered from ratio DB
           {'high': 27.74, 'low': 26.78, 'avrg': 27.26}
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    count = 0
    ratio_dict = {}

    if os.path.exists(db_ratio_flnm):
        with open(db_ratio_flnm, 'r') as fp_db:

            # Fill ratios from DB
            for line in fp_db.readlines():
                wrk_line = line.rstrip('\n')
                wrk_list = wrk_line.split(' ')
                tmp_key = wrk_list[0]
                if tmp_key in stash_dict.keys():
                    high = float(wrk_list[1])
                    low = float(wrk_list[2])
                    avrg = (high + low) / 2.0
                    ratio_dict[tmp_key] = {'high': high,
                                           'low': low,
                                           'avrg': avrg}
                    count += 1

            # Put 100% for non found keys
            if len(stash_dict.keys()) > count:
                for tmp_key in stash_dict.keys():
                    if tmp_key not in ratio_dict:
                        non_pkd = 100.00
                        ratio_dict[tmp_key] = {'high': non_pkd,
                                               'low': non_pkd,
                                               'avrg': non_pkd}

    return ratio_dict


def calc_diag_size(cf_x, cf_y, imean, grid, com_dict):
    """
    Calculates size required for storing diagnostic:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    cf_x - divider for number of columns
    cf_y - divider for number of rows
    imean - 2 for zonal mean, 3 for meridional
    grid - type of stash record
    com_dict - for model sizes
    Returns - dictionary of 3 variables:
        szbl - nearest integer in blocks of 512
        nx - modified
        ny - modified
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    dim_dict = {}
    l_endgame = com_dict['l_endgame']
    um_sect_sz = com_dict['um_sect_sz']

    if grid == "23":
        nx_p = com_dict['river_rowlen']
        ny_p = com_dict['river_rows']
    elif (grid == "11" or grid == "19") and l_endgame:
        # Model has global_rows in theta points
        nx_p = com_dict['gl_rowlen']
        ny_p = com_dict['gl_rows'] + 1
    elif grid == "14" and l_endgame:
        nx_p = 1
        ny_p = com_dict['gl_rows'] + 1
    else:
        nx_p = com_dict['gl_rowlen']
        ny_p = com_dict['gl_rows']

    if cf_y != 1:
        ny_p = ny_p / cf_y + 1
    if cf_x != 1:
        # This possibly will be used for specified area
        nx_p = nx_p / cf_x

    # Apply meaning options
    if imean == 2:
        nx_p = 1
    if imean == 3:
        ny_p = 1

    matrix_sz = nx_p * ny_p
    d_tmp = divmod(matrix_sz, um_sect_sz)
    n_int = d_tmp[0]
    n_frac = d_tmp[1]
    if n_frac > 0:
        n_int += 1

    dim_dict = {'szbl': n_int * um_sect_sz, 'nx': nx_p, 'ny': ny_p}
    return dim_dict


def create_report_records(item_dict, com_dict, use_dict,
                          time_dict, stash_dict,
                          ratio_dict, store_price, config):
    """
    Calculates data size for each stream
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    item_dict - gather info for each srash request
    com_dict - dictionary with common info
    use_dict - usage profile dictionary
    stash_dict - stash dictionary
    store_price - stotage TiB/per year
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    used_streams = sorted(use_dict['pp_file_lst'])
    mean_streams = sorted(use_dict['mean_tag_lst'])
    max_stream_number = use_dict['max_pp_num'] + 1
    mean_prds = com_dict['meanprds']
    row_format = '%6s %8s %8s %8s  %4d %3d %2d %13d %14d %14d %14d %4d %8.2f'

    # Packed sums
    pp_sum_y = [0 for k in range(max_stream_number)]
    pp_sum_q = [0 for k in range(max_stream_number)]
    pp_sum_m = [0 for k in range(max_stream_number)]
    pp_sum_d = [0 for k in range(max_stream_number)]

    # Meaning sums
    mn_sum_y = [0 for k in range(4)]
    mn_sum_q = [0 for k in range(4)]
    mn_sum_m = [0 for k in range(4)]
    mn_sum_d = [0 for k in range(4)]

    ff_data_start = [0 for k in range(max_stream_number)]
    ff_hdr_nodata = [0 for k in range(max_stream_number)]
    mn_data_start = [0 for k in range(4)]
    mn_hdr_nodata = [0 for k in range(4)]

    unpk_pp_sum_y = [0 for k in range(max_stream_number)]
    unpk_mn_sum_y = [0 for k in range(4)]
    num_pp_fields = [0 for k in range(max_stream_number)]
    num_mn_fields = [0 for k in range(4)]

    strm_frq = [0 for k in range(max_stream_number)]
    strm_frq_unit = [0 for k in range(max_stream_number)]
    strm_frq_hdrs = [1 for k in range(max_stream_number)]

    pp_lst = [[] for k in range(max_stream_number)]
    mn_pp_lst = [[] for k in range(4)]

    for each_key, rec in item_dict.iteritems():
        if rec['iopt'] == 3:
            # Calc output period
            e_lst = rec['iedt']
            s_lst = rec['isdt']
            # Keep prd for future use on interval output periods
            e_date = datetime.date(int(e_lst[0]), int(e_lst[1]), int(e_lst[2]))
            s_date = datetime.date(int(s_lst[0]), int(s_lst[1]), int(s_lst[2]))
            prd = (e_date - s_date).days / 365
        elif rec['iopt'] == 1:
            prd = com_dict['len_days'] / 360

        # Find out to which stream
        use_nm = rec['suse']
        u_rec = use_dict[use_nm]
        stream = u_rec['stream_n']

        # Find out time processing type
        time_nm = rec['stim']
        time_rec = time_dict[time_nm]
        time_proc_type = _get_var(config, time_rec, "ityp", type_="integer")
        dom_nm = rec['sdom']

        # Find out grid size, packing code and ratio
        tmp_list = each_key.rsplit("_")
        isec = tmp_list[0]
        item = tmp_list[1]
        isec = isec.rjust(2, "0")
        item = item.rjust(3, "0")
        stash_key = "1_" + isec + "_" + item
        msi_rec = stash_dict[stash_key]

        grid = msi_rec['grid']
        pkg_code = msi_rec['pkgcode']

        if pkg_code == "-99":
            msi_avrg = 100.00
        else:
            msi_ratio_rec = ratio_dict[stash_key]
            msi_avrg = msi_ratio_rec['avrg']

        dv_x = rec['div_x']
        dv_y = rec['div_y']
        imean = rec['imean']
        dsz = calc_diag_size(dv_x, dv_y, imean, grid, com_dict)
        mx_p = dsz['nx']
        my_p = dsz['ny']
        matrix_sz = dsz['szbl']

        # Do calculation for each active stream and climate meaning
        if ((stream in used_streams) or (stream in mean_streams and
                                         com_dict['l_mean_seq'])):
            # for all records except time series and user stash records
            if time_proc_type != 4 and time_proc_type != 8:
                freq_per_year = round(rec['kfreq'] * 360)
                if stream in used_streams:
                    to_stream_flag = 1
                    snum = u_rec['stream_n']
                    strm_frq[snum] = u_rec['ft_step']
                    strm_frq_unit[snum] = u_rec['reinit_un']
                    ff_data_start[snum] = u_rec['data_start']
                    ff_hdr_nodata[snum] = u_rec['hdr_nodata']

                    # Find out number of files with data in cases
                    # when period of reinitialization is one day or less
                    if strm_frq_unit[snum] == "hour" and strm_frq[snum] <= 24:
                        files_in_stream = 24 / strm_frq[snum]
                        # If diagnostic output freq less than number of files
                        # only each kfreq file will have non empty data
                        if rec['kfreq'] < files_in_stream:
                            strm_frq_hdrs[snum] = rec['kfreq']
                        else:
                            strm_frq_hdrs[snum] = files_in_stream
                else:
                    to_stream_flag = 0
                    indx = mean_streams.index(stream)
                    # correlate frequency for meaning outputs
                    mean_freq = com_dict['meanfreq']
                    if mean_freq[0] > 0:
                        freq_per_year /= mean_freq[0]

                    mn_data_start[indx] = u_rec['data_start']
                    mn_hdr_nodata[indx] = u_rec['hdr_nodata']

                if freq_per_year >= 360:
                    cf_y = cf_q = cf_m = cf_d = 1
                elif freq_per_year >= 12 and freq_per_year < 360:
                    cf_y = cf_q = cf_m = 1
                    cf_d = 0
                elif freq_per_year == 4:
                    cf_y = cf_q = 1
                    cf_m = cf_d = 0
                elif freq_per_year == 1:
                    cf_y = 1
                    cf_q = cf_m = cf_d = 0
                else:
                    cf_y = cf_q = cf_m = cf_d = 0

                number_of_fields = rec['vlevs'] * freq_per_year * cf_y
                full_size_y = rec['vlevs'] * matrix_sz * freq_per_year * cf_y
                full_size_m = cf_m * full_size_y / 12

                if mx_p > 1:
                    # Correlate size for packed fields
                    size_y = full_size_y * msi_avrg / 100.0
                else:
                    # One column fileld
                    size_y = full_size_y

                size_q = cf_q * size_y / 4
                size_m = cf_m * size_y / 12
                size_d = cf_d * size_y / 360

                # Correlate output size for meaning periods
                if to_stream_flag == 0:
                    size_y += 5 * size_m
                    size_q += size_m
                    full_size_y += 5 * full_size_m

                stkey_lst = stash_key.split("_")
                mm_iii = stkey_lst[1].rjust(2) + "_" + stkey_lst[2].zfill(3)

                d_prof = dom_nm
                t_prof = time_nm
                u_prof = use_nm
                row_members = (mm_iii, d_prof, t_prof, u_prof, mx_p, my_p,
                               rec['vlevs'], round(size_d), round(size_m),
                               round(size_q), round(size_y), int(pkg_code),
                               msi_avrg)
                pp_line = row_format % row_members
                if msi_avrg == 100.00 and pkg_code != "-99":
                    pp_line = pp_line + "_#"
                if msi_avrg != 100.00 and mx_p == 1:
                    pp_line = pp_line + "_s"

                if to_stream_flag:
                    unpk_pp_sum_y[snum] += full_size_y
                    pp_sum_y[snum] += size_y
                    pp_sum_q[snum] += size_q
                    pp_sum_m[snum] += size_m
                    pp_sum_d[snum] += size_d
                    pp_lst[snum].append(pp_line)
                    num_pp_fields[snum] += number_of_fields
                else:
                    unpk_mn_sum_y[indx] += full_size_y
                    mn_sum_y[indx] += size_y
                    mn_sum_q[indx] += size_q
                    mn_sum_m[indx] += size_m
                    mn_sum_d[indx] += size_d
                    mn_pp_lst[indx].append(pp_line)
                    num_mn_fields[indx] += number_of_fields

            else:
                # Ignore time series but show diags marked
                row_format_ign = '%17s %2d %44s %26s %3d'
                row_members = (" ", grid, "** ignored **", " ", int(pkg_code))
                pp_line = row_format_ign % row_members
                if stream in used_streams:
                    snum = u_rec['stream_n']
                    pp_lst[snum].append(pp_line)

    # Show data size in print format
    print_report_records(max_stream_number, mean_prds,
                         mean_streams,
                         num_pp_fields, num_mn_fields,
                         pp_sum_y, pp_sum_q, pp_sum_m, pp_sum_d,
                         mn_sum_y, mn_sum_q, mn_sum_m, mn_sum_d,
                         unpk_pp_sum_y, unpk_mn_sum_y,
                         pp_lst, mn_pp_lst, ff_data_start,
                         ff_hdr_nodata, strm_frq_hdrs,
                         strm_frq, strm_frq_unit,
                         mn_data_start, mn_hdr_nodata,
                         store_price)


def print_report_records(max_stream_number, mean_prds,
                         mean_streams,
                         num_pp_fields, num_mn_fields,
                         pp_sum_y, pp_sum_q, pp_sum_m, pp_sum_d,
                         mn_sum_y, mn_sum_q, mn_sum_m, mn_sum_d,
                         unpk_pp_sum_y, unpk_mn_sum_y,
                         pp_lst, mn_pp_lst, ff_data_start,
                         ff_hdr_nodata, strm_frq_hdrs,
                         strm_frq, strm_frq_unit,
                         mn_data_start, mn_hdr_nodata,
                         store_price):
    """
    Show info about data in each stream
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    max_stream_number - number of used streams
    mean_prds - list of meaning periods
    num_pp_fields - number of fields in pp files
    num_mn_fields - number of fields in mean files
    pp_sum_y - stream sums of packed data for periods: year
    pp_sum_q - quarter
    pp_sum_m - month
    pp_sum_d - day
    mn_sum_y - sums of packed data for meaning files
    mn_sum_q - quarter
    mn_sum_m - month
    mn_sum_d - day
    unpk_pp_sum_y - stream sum of data if unpacked
    unpk_mn_sum_y - meaning file sum of data if unpacked
    pp_lst - list of diagnostic outputs in stream files
    mn_pp_lst -list of diagnostic outputs in meaning files
    ff_data_start - position of data in fileds file
    ff_hdr_nodata - size of header with empty data
    strm_frq_hdrs - number of files in stream with data
    mn_data_start - position of data in mean file
    strm_frq - period of file reinitialisation


    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    title_0 = "======================================================================================================================="
    title_1 = "Item             Profile            Dimension           Avrg           Avrg           Avrg           Avrg   Pkg   Ratio"
    title_2 = "code       Domain   Time      Use   X * Y * Z          p/day         p/mnth          p/qtr           p/yr   code   avrg"
    line_br = "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
    stream_unline = "-------------~------------------------------------------------------"
    stream_hdr1 = "Stream number %2d with period of initialization every %d %s(s)"
    text_n = "Fields in one file:          "
    text_t = "Total data per period:"
    text_f = "UM fields file size per period:"
    text_p = "PP file size per period:"
    text_g = "PP file size per period (MiB):"
    text_m = "Total file sizes for meaning:"
    text_c = "Cost of storage TB per year (GBP):"
    text_total = "Total cost per job (GBP):"
    hdr_format = '%-27s %14d'
    sum_format = '%-33s %26d %14d %14d %14d      %8.2f'
    size_format = '%-33s %26d %14d %14d %14d'
    size_format_gb = '%-36s %26.2f %14.2f %14.2f %14.2f'
    cost_format = '%-34s %70s %13.2f'

    tot_cost_pp_y = tot_cost_mn_y = 0

    print "Storage of 1TB per 2016 year:", store_price, "GBP"

    # Print file sizes and item list for pp streams
    for k in range(max_stream_number):
        if pp_sum_y[k] > 0:
            pp_lst[k].sort()
            stream_number = k

            print ""
            # Header of the stream
            stream_members = (stream_number, strm_frq[k], strm_frq_unit[k])
            stream_ln = stream_hdr1 % stream_members
            print stream_ln
            print stream_unline

            # Fields information
            stream_ln1 = hdr_format % ("Number of files daily:",
                                       strm_frq_hdrs[k])
            stream_ln2 = hdr_format % ("UM fields file header size:",
                                       ff_hdr_nodata[k] * 8)
            stream_ln3 = hdr_format % ("Data start position:",
                                       ff_data_start[k] * 8)
            stream_ln4 = hdr_format % ("Total fields per year:",
                                       int(num_pp_fields[k]))
            print stream_ln1
            print stream_ln2
            print stream_ln3
            print stream_ln4

            # Refine size of headers
            hdr_correct_d = hdr_correct_m = hdr_correct_q = \
                hdr_correct_y = ff_data_start[k]
            ppcf_y = ppcf_q = ppcf_m = ppcf_d = 1
            if pp_sum_d[k] == 0:
                hdr_correct_d = ff_hdr_nodata[k]
                ppcf_d = 0
            if pp_sum_m[k] == 0:
                hdr_correct_m = ff_hdr_nodata[k]
                ppcf_m = 0
            if pp_sum_q[k] == 0:
                hdr_correct_q = ff_hdr_nodata[k]
                ppcf_q = 0
            if pp_sum_y[k] == 0:
                hdr_correct_y = ff_hdr_nodata[k]
                ppcf_y = 0

            # Number of fields in one file
            stream_members = \
                (text_n,
                 int(num_pp_fields[k] / (strm_frq_hdrs[k]*360)) * ppcf_d,
                 int(num_pp_fields[k] / (strm_frq_hdrs[k]*12)) * ppcf_m,
                 int(num_pp_fields[k] / (strm_frq_hdrs[k]*4)) * ppcf_q,
                 int(num_pp_fields[k] / strm_frq_hdrs[k]) * ppcf_y)
            stream_ln = size_format % stream_members
            print stream_ln

            print title_0
            print title_1
            print title_2
            print title_0

            # Print detailed lines for each request
            for itm_ln in pp_lst[k]:
                print itm_ln
            print line_br

            # Print total data size per period
            sz_inpc = pp_sum_y[k] * 100.0 / unpk_pp_sum_y[k]
            btm_memb = (text_t, pp_sum_d[k],
                        pp_sum_m[k], pp_sum_q[k], pp_sum_y[k],
                        round(sz_inpc, 2))
            btm_line_1 = sum_format % btm_memb
            print btm_line_1

            # UM fields file
            btm_memb = \
                (text_f,
                 (hdr_correct_d * strm_frq_hdrs[k] + pp_sum_d[k]) * 8,
                 (hdr_correct_m * strm_frq_hdrs[k] + pp_sum_m[k]) * 8,
                 (hdr_correct_q * strm_frq_hdrs[k] + pp_sum_q[k]) * 8,
                 (hdr_correct_y * strm_frq_hdrs[k] + pp_sum_y[k]) * 8)
            btm_line_2 = size_format % btm_memb
            print btm_line_2

            # PP file per day, month, quarter, year
            sz_pp_d = (pp_sum_d[k] + 68 *
                       int(num_pp_fields[k]) / 360) * 4 * ppcf_d
            sz_pp_m = (pp_sum_m[k] + 68 *
                       int(num_pp_fields[k]) / 12) * 4 * ppcf_m
            sz_pp_q = (pp_sum_q[k] + 68 *
                       int(num_pp_fields[k]) / 4) * 4 * ppcf_q
            sz_pp_y = (pp_sum_y[k] + 68 *
                       int(num_pp_fields[k])) * 4 * ppcf_y

            btm_memb = (text_p, sz_pp_d, sz_pp_m, sz_pp_q, sz_pp_y)
            btm_line_3 = size_format % btm_memb
            print btm_line_3

            # Convert to MiB
            btm_memb_mb = (text_g, sz_pp_d / 1048576.0,
                           sz_pp_m / 1048576.0,
                           sz_pp_q / 1048576.0,
                           sz_pp_y / 1048576.0)
            btm_line_4 = size_format_gb % btm_memb_mb
            print btm_line_4

            # PP file size (in MiB) with headers
            gb_pp_sum_y = ((pp_sum_y[k] + 68 * int(num_pp_fields[k])) * 4
                           / 1048576.0)

            # Cost per TiB
            tb_cost_pp_sum_y = gb_pp_sum_y * store_price / 1048576.0
            btm_memb = (text_c, " ", tb_cost_pp_sum_y)
            btm_line_5 = cost_format % btm_memb
            print btm_line_5
            print ""
            tot_cost_pp_y += tb_cost_pp_sum_y

    # Climate Meaning records
    # =======================

    for k in range(4):
        if mn_sum_y[k] > 0:
            mn_pp_lst[k].sort()
            unit_file = mean_streams[k]

            print ""
            # Header of meaning file
            sub_title_format = \
                'File Unit %2s for the climate meaning periods %s'
            sub_title_members = (unit_file, mean_prds)
            sub_title_ln = sub_title_format % sub_title_members
            print sub_title_ln

            stream_ln2 = hdr_format % ("UM fields file header size:",
                                       mn_hdr_nodata[k] * 8)
            stream_ln3 = hdr_format % ("Data start position:",
                                       mn_data_start[k] * 8)
            stream_ln4 = hdr_format % ("Total fields per year:",
                                       int(num_mn_fields[k]))
            print stream_ln2
            print stream_ln3
            print stream_ln4
            print stream_unline

            print title_0
            print title_1
            print title_2
            print title_0

            # Print detailed lines for each mean request
            for itm_ln in mn_pp_lst[k]:
                print itm_ln
            print line_br

            # Print total data size per period
            sz_inpc = mn_sum_y[k] * 100.0 / unpk_mn_sum_y[k]
            btm_memb = (text_t, mn_sum_d[k], mn_sum_m[k], mn_sum_q[k],
                        mn_sum_y[k], round(sz_inpc, 2))
            btm_line_1 = sum_format % btm_memb
            print btm_line_1

            # Calculate size of UM field files and pp files for meaning periods
            hdr_correct_d = hdr_correct_m = hdr_correct_q = \
                hdr_correct_y = mn_data_start[k]
            mncf_y = mncf_q = mncf_m = mncf_d = 1
            if mn_sum_d[k] == 0:
                hdr_correct_d = mn_hdr_nodata[k]
                mncf_d = 0
            if mn_sum_m[k] == 0:
                hdr_correct_m = mn_hdr_nodata[k]
                mncf_m = 0
            if mn_sum_q[k] == 0:
                hdr_correct_q = mn_hdr_nodata[k]
                mncf_q = 0
            if mn_sum_y[k] == 0:
                hdr_correct_y = mn_hdr_nodata[k]
                mncf_y = 0

            # UM fields file
            btm_memb = (text_m,
                        (hdr_correct_d + mn_sum_d[k]) * 8,
                        (hdr_correct_m + mn_sum_m[k]) * 8,
                        (hdr_correct_q + mn_sum_q[k]) * 8,
                        (hdr_correct_y + mn_sum_y[k]) * 8,
                        round(sz_inpc, 2))

            btm_line_2 = sum_format % btm_memb
            print btm_line_2

            # PP file per day, month, quarter, year
            sz_mn_d = (mn_sum_d[k] + 68 *
                       int(num_mn_fields[k]) / 360) * 4 * mncf_d
            sz_mn_m = (mn_sum_m[k] + 68 *
                       int(num_mn_fields[k]) / 12) * 4 * mncf_m
            sz_mn_q = (mn_sum_q[k] + 68 *
                       int(num_mn_fields[k]) / 4) * 4 * mncf_q
            sz_mn_y = (mn_sum_y[k] + 68 *
                       int(num_mn_fields[k])) * 4 * mncf_y

            btm_memb = (text_p, sz_mn_d, sz_mn_m, sz_mn_q, sz_mn_y)
            btm_line_3 = size_format % btm_memb
            print btm_line_3

            # Convert to MiB
            btm_memb_mb = (text_g, sz_mn_d / 1048576.0,
                           sz_mn_m / 1048576.0,
                           sz_mn_q / 1048576.0,
                           sz_mn_y / 1048576.0)
            btm_line_4 = size_format_gb % btm_memb_mb
            print btm_line_4

            # Cost per TiB
            gb_mn_sum_y = (mn_sum_y[k] * 4) / 1048576.0
            tb_cost_mn_sum_y = gb_mn_sum_y * store_price / 1048576.0
            btm_memb = (text_c, " ", tb_cost_mn_sum_y)
            btm_line_5 = cost_format % btm_memb
            print btm_line_5
            tot_cost_mn_y += tb_cost_mn_sum_y

    # print total per job
    btm_memb = (text_total, " ", tot_cost_pp_y + tot_cost_mn_y)
    total_line = cost_format % btm_memb
    print ""
    print line_br
    print total_line


def get_usr_args():
    """
    Reset default settings and show help
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    --s - directory path of user stash master file
    --d - locaton of DB ratios
    --c - cost of storage
    --h - show help
    --? - show help
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    # Directory to DB packing ratio, based of previous runs
#    db_ratio_flnm = '/home/h04/hadip/data_tmp/DB_ratio'
    db_ratio_flnm = "/home/h04/umui/adm_umui/DB_ratio"

    # Directory path to default location of Stash file
    stash_path = \
    "/home/h03/fcm/rose-meta/GA7/ga6_136.18.1_vn10.3/etc/stash/STASHmaster"

    # Storage cost of 1TB per year
    storage_cost = 85.0      # year 2016

    str_1 = "\nNavigate to the directory where the rose-app.conf file is\n"
    str_2 = "Example: suite_datasz.py > file_output\n"
    str_3 = "Options: --s path to user stash file\n"
    str_4 = "         --d location of ratio Data Base"

    help_str = str_1 + str_2 + str_3 + str_4
    show_help = False

    args_dict = {'stash_path': stash_path, 'db_ratio_flnm': db_ratio_flnm,
                 'help_str': help_str, 'show_help': show_help,
                 'storage_cost': storage_cost}

    if len(sys.argv) > 1:
        arglist = sys.argv
        for item in arglist:
            if item == "--s":
                ind = arglist.index(item)
                stash_path = arglist[ind+1]
                args_dict['stash_path'] = stash_path
            if item == "--d":
                ind = arglist.index(item)
                db_ratio_flnm = arglist[ind+1]
                args_dict['db_ratio_flnm'] = db_ratio_flnm
            if item == "--c":
                ind = arglist.index(item)
                storage_cost = arglist[ind+1]
                args_dict['storage_cost'] = float(storage_cost)
            if (item == "--h" or "--?") and len(sys.argv) == 2:
                show_help = True
                args_dict['show_help'] = True

    return args_dict


def main():
    """ Access suite config file and produce report """

    # Replace default settings with user supplied ones
    args_dict_s = get_usr_args()
    if args_dict_s['show_help']:
        print args_dict_s['help_str']
        exit()

    # Get access to rose_app.conf namelist vars
    conf_dir = os.getcwd()
    file_name_conf = os.path.join(conf_dir, "rose-app.conf")
    with open(file_name_conf, 'r') as fp_conf:

        try:
            config_s = rose.config.load(fp_conf)

        except rose.config.ConfigSyntaxError:
            print "Cannot find " + file_name_conf
            print "Change to the directory where the rose-app.conf file is"
            print args_dict_s['help_str']

    storage_cost_s = args_dict_s['storage_cost']
    db_ratio_flnm_s = args_dict_s['db_ratio_flnm']
    stash_path_s = args_dict_s['stash_path']
    file_name = os.path.join(stash_path_s, "STASHmaster_A")
    print "STASHmaster file used:        " + file_name
    print "Config file used:             " + file_name_conf

    # Get info about all stash records
    parser = StashMasterParserv1(stash_path_s)
    stash_lookup_s = parser.get_lookup_dict()
    exppxi_s = Exppxi(stash_lookup_s)

    # Initialise dictionaries
    stash_dict_s = {}
    ratio_dict_s = {}
    use_dict_s = {}
    item_dict_s = {}
    time_dict_s = {}
    com_dict_s = {}

    # Create common to all requests dictionary
    # --------------------------------------
    com_dict_s = create_com_dict(config_s)
    # Print common dictionary
    # for k,j in com_dict_s.iteritems():
    #     print 'COMMON dictionary ', k, j

    # Filter all usage profiles with locn = 3 || 2
    use_dict_s = usage_prof_desc(config_s)

    # Print "Selected usage profiles "
    # for k,j in use_dict_s.iteritems():
    #     print "key ", k, "value ", j

    if len(use_dict_s) != 0:
        # Do the rest of calculations
        uprof_keys = use_dict_s.keys()

        # Select only requests with usage profiles for PP and mean files
        item_dict_s = form_request_keys(config_s, uprof_keys)

        # Create lists of domain and time profiles involved in request
        time_lst = []
        domain_lst = []

        for wrk_key in item_dict_s.keys():
            tmp_list_s = wrk_key.rsplit("_")
            domain_lst.append(tmp_list_s[2])
            time_lst.append(tmp_list_s[3])

        domain_keys = list(set(domain_lst))
        time_keys = list(set(time_lst))

        # print "domain keys: ", domain_keys
        # print "time_keys: ", time_keys

        # Create domain profile dictionary for ones used in requests
        domain_dict = create_prof_dict(config_s,
                                       'namelist:domain(', 'dom_name',
                                       domain_keys)

        # Create time profile dictionary for ones used in requests
        time_dict_s = create_prof_dict(config_s, 'namelist:time(',
                                       'tim_name', time_keys)

        # Print domain dictionaly
        # for k,j in domain_dict.iteritems():
        #     print 'selected domains  ', k, j

        # Print time dictionaly
        # for k,j in time_dict_s.iteritems():
        #     print 'selected time profiles  ', k, j

        # Add vertical dimention to diagnostics
        item_dict_s = add_vlevels(item_dict_s, domain_dict, config_s)

        # Add horizontal area to diagnostics
        item_dict_s = add_horiz_area(item_dict_s, domain_dict, config_s)

        # Add output frequency to diagnostics and time-series code
        item_dict_s = add_outfreq(item_dict_s, time_dict_s, com_dict_s,
                                  config_s)

        # Add grid type and package code from STASH file
        stash_dict_s = fill_stash_dict(item_dict_s, exppxi_s)

        # Print stash dictionary
        # for k,j in stash_dict_s.iteritems():
        #     print 'STASH dictionary ', k, j

        # Add packing ratio from DB
        ratio_dict_s = fill_ratio_dict(db_ratio_flnm_s, stash_dict_s)

        # Print ratio dictionary
        # for k,j in ratio_dict_s.iteritems():
        #     print 'RATIO dictionary ', k, j

        # Create report
        create_report_records(item_dict_s, com_dict_s, use_dict_s,
                              time_dict_s, stash_dict_s, ratio_dict_s,
                              storage_cost_s, config_s)
    else:
        print "No requests to FF streams found"


if __name__ == '__main__':
    main()
