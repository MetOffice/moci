# -*- coding: iso-8859-1 -*-
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""This module contains code to validate STASH requests and profiles."""
import os.path
import sys
import rose.macro

META_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_DIR = os.path.dirname(os.path.dirname(META_PYTHON_DIR))
sys.path.append(META_PYTHON_DIR)
import widget.stash_parse

STASHMASTER_PATH = os.path.join(META_DIR, "etc", "stash",
                                "STASHmaster")
#META_DIR = os.path.dirname(  # lib
#              os.path.dirname(  # python
#                 os.path.dirname(  # widget
#                    os.path.dirname(os.path.abspath(__file__)))))


class STASHTstmskValidate(rose.macro.MacroBase):
    """Make sure STASH requests are available."""

    error_text = "Unavailable STASH item: {0}"

    def validate(self, config, meta_config=None):
        """Check availability of STASH requests."""
        parser = widget.stash_parse.StashMasterParserv1(STASHMASTER_PATH)
        # create dictionary of all stash records
        stash_lookup = parser.get_lookup_dict()
        exppxi = Exppxi(stash_lookup)

        isec_item_dict = {}
        for section, sect_node in config.value.items():
            if (not sect_node.is_ignored() and
                    section.startswith("namelist:streq(") and
                    isinstance(sect_node.value, dict)):
                isec = sect_node.get(["isec"], no_ignore=True)
                item = sect_node.get(["item"], no_ignore=True)
                if isec is not None and item is not None:
                    str_sec = str(isec.value)
                    str_item = str(item.value)
                    zf_sec = str_sec.zfill(3)
                    zf_item = str_item.zfill(3)
                    sec_item_key = zf_sec + "_" + zf_item
                    isec_item_dict.setdefault(sec_item_key, []).append(section)
        imodl = 0  # First element
        # get section versions for mask testing only once
        n_internal_model_max = 2
        h_vers = _get_hvers(config, n_internal_model_max, nsectp=99)

        for each_key in sorted(isec_item_dict.iterkeys()):
            nsec = each_key.split("_")[0]
            nitem = each_key.split("_")[1]
            # remove leading zeros
            if nsec == "000":
                nsec = "0"
            else:
                nsec = nsec.lstrip("0")
            nitem = nitem.lstrip("0")
            msk_chk_tu = tstmsk(config, imodl, nsec, nitem, h_vers, exppxi)
            l_mask = msk_chk_tu[0]
            msg = each_key + " " + msk_chk_tu[1]
            if not l_mask:
                bad_sections = isec_item_dict[each_key]
                for bad_section in sorted(bad_sections):
                    self.add_report(bad_section, None, None,
                                    self.error_text.format(msg))
        return self.reports


class ItemsTstmskValidate(rose.macro.MacroBase):
    """Make sure items requests in reconfiguration are valid"""
    
    error_text = "Invalid stash_req: {0}"

    def validate(self, config, meta_config=None):
        """Check availability of items requests."""
        parser = widget.stash_parse.StashMasterParserv1(STASHMASTER_PATH)
        # create dictionary of all stash records
        stash_lookup = parser.get_lookup_dict()
        exppxi = Exppxi(stash_lookup)
        items_stash_mapping = []
        for section, sect_node in config.value.items():
            # Loop over config file and find all items namelists
            if (not sect_node.is_ignored() and
                    section.startswith("namelist:items(") and
                    isinstance(sect_node.value, dict)):
                # Split possible multiple stash requests from each items namelist
                stash_req = sect_node.get(["stash_req"], 
                                          no_ignore=True).value.split(",")
                if stash_req is not None:
                    # section in following line is rose app section
                    # not stash section
                    items_stash_mapping.append((section, stash_req))
        # Setup variables needed by tstmsk routine
        imodl = 0  # First element
        # get section versions for mask testing only once
        n_internal_model_max = 2
        h_vers = _get_hvers(config, n_internal_model_max, nsectp=99)
        for items_nl, stash_req in items_stash_mapping:
            for stash_code in stash_req:
                # Convert stash_req into separate item and section code, i.e.
                # 222 is section 0, item 222 and 34002 is section 34, item 2
                stash_section = str(int(stash_code)/1000)
                stash_item = str(int(stash_code) - (1000*int(stash_section)))
                try:
                    tstmsk_tuple = tstmsk(config, imodl, stash_section, 
                                          stash_item, h_vers, exppxi)
                except STASHNotFoundError as e:
                    print "[WARN] " + str(e)
                    print ("[WARN] Items request contains field not present in"
                           " STASHmaster. Unable to perform tstmsk "
                           "verification")
                    continue
                valid_stash = tstmsk_tuple[0]
                error_msg = tstmsk_tuple[1]
                if not valid_stash:
                    msg = stash_code + " : " + error_msg
                    self.add_report(items_nl, None, None,
                                    self.error_text.format(msg))
        return self.reports

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
        try:
            section = self.stash_lookup[isec]
        except KeyError:
            raise STASHNotFoundError("STASHmaster section {0} not found"
                                     .format(isec))
        try:
            temp_item = section[item]
        except KeyError:
            raise STASHNotFoundError("STASHmaster record not found for" 
                                     + " section {0} item {1}"
                                     .format(isec,item))
        try:
            element = temp_item[element_name]
        except KeyError:
            raise STASHNotFoundError("STASHmaster element {0} not found"
                                     .format(element_name))
        return element


class STASHNotFoundError(KeyError):
    """Report if unable to locate valid item, section or element in 
    STASHmaster"""
    def __str__(self):
        return self.args[0]

class OptionNotFoundError(KeyError):
    """Report if unable to locate valid option code"""
    def __str__(self):
        return self.args[0]

class ConfigItemNotFoundError(KeyError):
    """Report a missing configuration item."""

    ERROR_MISSING = "Cannot find configuration setting: {0}"

    def __str__(self):
        if len(self.args) > 1:
            id_ = self.args[0] + "=" + self.args[1]
        else:
            id_ = self.args[0]

        return self.ERROR_MISSING.format(id_)


def tstmsk(config, modl, isec, item, h_vers, exppxi):

    """Checks version mask and option code in a ppx record.
    Return False if there is a problem, True otherwise.
    """

    # At the beginning status of all items is True
    # If some of tests fails set to False and DO NOT re-initialise it
    l_mask = True
    a_im = 1
    nsec = int(isec)

    # up to 150 tracers now allowed for sections 33,34,36,37
    a_max_trvars = 150
    a_max_ukcavars = 150

    # if the section not used, set requested items to false
    nmask = h_vers[a_im - 1][nsec]
    if nmask == 0 or nmask is None:
        l_mask = False
        msg = ":section " + str(nsec) + " not used or undefined"
        rc_tu = (l_mask, msg)
        return rc_tu
    else:
        # validate version mask of stash item
        smsk = exppxi.get(isec, item, "version_mask")
        imsk = int(smsk, base=2)
        twonm = 2**nmask
        twonm1 = 2**(nmask-1)
        imod = (imsk % twonm) / twonm1
        if imod == 0:
            # item not available for this section version
            l_mask = False
            msg = smsk + " invalid version mask"
            rc_tu = (l_mask, msg)
            return rc_tu

    # validate option codes
    # changes must be synchronised with UM procedure tstmsk
    # option codes have the same var names n0,...,n30, n2n1, n10n9
    # get iopn using string indexes
    # in stash record numbering option codes starts from right to left
    msg = ""
    iopn = exppxi.get(isec, item, "option_codes")
    sum_iopn = int(iopn)
    n2n1 = int(iopn[30 - 2:])
    n1 = int(iopn[30 - 1])
    n2 = int(iopn[30 - 2])
    n3 = int(iopn[30 - 3])
    n4 = int(iopn[30 - 4])
    n5 = int(iopn[30 - 5])
    n6 = int(iopn[30 - 6])
    n7 = int(iopn[30 - 7])
    n8 = int(iopn[30 - 8])
    n9 = int(iopn[30 - 9])
    n10n9 = int(iopn[30 - 10:30 - 8])
    n10 = int(iopn[30 - 10])
    n11 = int(iopn[30 - 11])
    n12 = int(iopn[30 - 12])
    n13 = int(iopn[30 - 13])
    n14 = int(iopn[30 - 14])
    n15 = int(iopn[30 - 15])
    n16 = int(iopn[30 - 16])
    n17 = int(iopn[30 - 17])
    n18 = int(iopn[30 - 18])
    n19 = int(iopn[30 - 19])
    n20 = int(iopn[30 - 20])
    n21 = int(iopn[30 - 21])
    n22 = int(iopn[30 - 22])
    n23 = int(iopn[30 - 23])
    n24 = int(iopn[30 - 24])
    n25 = int(iopn[30 - 25])
    n26 = int(iopn[30 - 26])
    n27 = int(iopn[30 - 27])
    n28 = int(iopn[30 - 28])
    n29 = int(iopn[30 - 29])
    n30 = int(iopn[30 - 30])

    l_top = _get_var(config, "namelist:jules_hydrology", "l_top",
                     type_="logical")
    l_use_biogenic = _get_var(config, "namelist:run_radiation",
                     "l_use_biogenic", type_="logical")
    l_use_arclbiom = _get_var(config, "namelist:run_radiation",
                     "l_use_arclbiom", type_="logical")
    l_use_arclblck = _get_var(config, "namelist:run_radiation",
                     "l_use_arclblck", type_="logical")
    l_use_arclsslt = _get_var(config, "namelist:run_radiation",
                     "l_use_arclsslt", type_="logical")
    l_use_arclsulp = _get_var(config, "namelist:run_radiation",
                     "l_use_arclsulp", type_="logical")
    l_use_arcldust = _get_var(config, "namelist:run_radiation",
                     "l_use_arcldust", type_="logical")
    l_use_arclocff = _get_var(config, "namelist:run_radiation",
                     "l_use_arclocff", type_="logical")
    l_use_arcldlta = _get_var(config, "namelist:run_radiation",
                     "l_use_arcldlta", type_="logical")
    formdrag = _get_var(config, "namelist:jules_surface", "formdrag",
                      type_="integer")
    i_gwd_vn = _get_var(config, "namelist:run_gwd",
                     "i_gwd_vn", type_="integer")
    h_global = _get_var(config, "namelist:model_domain",
                     "model_type", type_="integer")
    l_oasis_timers = _get_var(config, "namelist:coupling_control", 
                              "l_oasis_timers",
                              default=False, type_="logical")
    coupler = _get_var(config, "env", "COUPLER", default="",
                      type_="character")
    l_oasis = False
    if coupler != "":
        l_oasis = True
    l_oasis_icecalve = _get_var(config, "namelist:coupling_control",
                     "l_oasis_icecalve", default=False, type_="logical")
    l_sstanom = _get_var(config, "namelist:ancilcta", "l_sstanom", 
                      type_="logical")
    iscrntdiag = _get_var(config, "namelist:jules_surface",
                     "iscrntdiag", type_="integer")
    isrfexcnvgust = _get_var(config, "namelist:jules_surface",
                     "isrfexcnvgust", type_="integer")
    l_murk = _get_var(config, "namelist:run_murk", "l_murk",
                     default=False, type_="logical")
    l_murk_source = _get_var(config, "namelist:run_murk", "l_murk_source",
                     default=False,  type_="logical")
    nsmax = _get_var(config, "namelist:jules_snow", "nsmax", type_="integer")
    l_snow_albedo = _get_var(config, "namelist:jules_radiation",
                     "l_snow_albedo", default=False, type_="logical")
    l_embedded_snow = _get_var(config, "namelist:jules_radiation",
                     "l_embedded_snow", default=False, type_="logical")
    i_bl_vn = _get_var(config, "namelist:run_bl", "i_bl_vn", type_="integer")
    l_emcorr = _get_var(config, "namelist:run_eng_corr", "l_emcorr",
                      type_="logical")
    l_use_electric = _get_var(config, "namelist:run_electric",
                     "l_use_electric", default=False, type_="logical")
    if l_use_electric:
        electric_method = _get_var(config, "namelist:run_electric",
                           "electric_method", type_="integer")
    else:
        electric_method = None


    # Sea ice
    l_sice_meltponds_cice = _get_var(config, "namelist:jules_sea_seaice",
                     "l_sice_meltponds_cice", default=False, type_="logical")
    l_saldep_freeze = _get_var(config, "namelist:jules_sea_seaice",
                     "l_saldep_freeze", default=False, type_="logical")


    # Sulphur cycle (1-19)
    l_sulpc_so2 = _get_var(config, "namelist:run_aerosol",
                     "l_sulpc_so2", default=False, type_="logical")
    l_so2_surfem = _get_var(config, "namelist:run_aerosol",
                     "l_so2_surfem", default=False, type_="logical")
    l_so2_hilem = _get_var(config, "namelist:run_aerosol",
                     "l_so2_hilem", default=False, type_="logical")
    l_so2_natem = _get_var(config, "namelist:run_aerosol",
                     "l_so2_natem", default=False, type_="logical")
    l_sulpc_dms = _get_var(config, "namelist:run_aerosol",
                     "l_sulpc_dms", default=False, type_="logical")
    l_dms_em = _get_var(config, "namelist:run_aerosol",
                     "l_dms_em", default=False, type_="logical")
    l_sulpc_online_oxidants = _get_var(config, "namelist:run_aerosol",
                     "l_sulpc_online_oxidants", default=False,
                      type_="logical")
    l_sulpc_ozone = _get_var(config, "namelist:run_aerosol",
                     "l_sulpc_ozone", default=False, type_="logical")
    l_sulpc_nh3 = _get_var(config, "namelist:run_aerosol",
                     "l_sulpc_nh3", default=False, type_="logical")
    l_nh3_em = _get_var(config, "namelist:run_aerosol",
                     "l_nh3_em", default=False, type_="logical")

    # Soot (21 - 23)
    l_soot = _get_var(config, "namelist:run_aerosol",
                     "l_soot", default=False, type_="logical")
    l_soot_surem = _get_var(config, "namelist:run_aerosol",
                     "l_soot_surem", default=False, type_="logical")
    l_soot_hilem = _get_var(config, "namelist:run_aerosol",
                     "l_soot_hilem", default=False, type_="logical")

    # Biomass (24 - 26)
    l_biomass = _get_var(config, "namelist:run_aerosol",
                     "l_biomass", default=False, type_="logical")
    l_bmass_surem = _get_var(config, "namelist:run_aerosol",
                     "l_bmass_surem", default=False, type_="logical")
    l_bmass_hilem = _get_var(config, "namelist:run_aerosol",
                     "l_bmass_hilem", default=False, type_="logical")

    # 2 bin and 6 bin Mineral dust
    i_dust = _get_var(config, "namelist:run_dust", "i_dust", type_="integer")
    l_dust = False
    l_dust_diag = False
    if i_dust == 1:
        l_dust = True
        l_dust_diag = False
    elif i_dust == 2:
        l_dust = False
        l_dust_diag = True

    # Nitrate (31)
    l_nitrate = _get_var(config, "namelist:run_aerosol",
                     "l_nitrate", default=False, type_="logical")

    # OCFF (35-37)
    l_ocff = _get_var(config, "namelist:run_aerosol",
                     "l_ocff", default=False, type_="logical")
    l_ocff_surem = _get_var(config, "namelist:run_aerosol",
                     "l_ocff_surem", default=False, type_="logical")
    l_ocff_hilem = _get_var(config, "namelist:run_aerosol",
                     "l_ocff_hilem", default=False, type_="logical")

    # 6 bin only Mineral dust
    l_twobin_dust = _get_var(config, "namelist:run_dust",
                     "l_twobin_dust", default=False, type_="logical")
    l_triffid = _get_var(config, "namelist:jules_vegetation",
                     "l_triffid", type_="logical")
    l_albedo_obs = _get_var(config, "namelist:jules_radiation",
                     "l_albedo_obs", type_="logical")
    l_spec_albedo = _get_var(config, "namelist:jules_radiation",
                     "l_spec_albedo", type_="logical")
    l_aggregate = _get_var(config, "namelist:jules_surface",
                     "l_aggregate", type_="logical")
    i_aggregate_opt = _get_var(config, "namelist:jules_surface",
                     "i_aggregate_opt", default=0,
                      type_="integer")
    l_vary_z0m_soil = _get_var(config, "namelist:jules_surface",
                     "l_vary_z0m_soil", type_="logical")
    l_mcr_qcf2 = False # Hard codded in mphys_inputs_mod.f90
    l_mcr_qrain = _get_var(config, "namelist:run_precip",
                     "l_mcr_qrain", type_="logical")
    l_mcr_qgraup = _get_var(config, "namelist:run_precip",
                     "l_mcr_qgraup", type_="logical")
    l_subgrid_qcl_mp = _get_var(config, "namelist:run_precip",
                         "l_subgrid_qcl_mp", default=False, type_="logical")
    l_casim = False # Hard coded in mphys_inputs_mod.F90 for now.
#    l_casim = _get_var(config, "namelist:run_precip",
#                         "l_casim", type_="logical")
    l_pc2 = _get_var(config, "namelist:run_cloud", "l_pc2", type_="logical")
    l_3d_cca = _get_var(config, "namelist:run_convection", "l_3d_cca",
                      default=False, type_="logical")
    l_ccrad = _get_var(config, "namelist:run_convection", "l_ccrad",
                      default=False, type_="logical")
    l_conv_hist = _get_var(config, "namelist:run_convection",
                     "l_conv_hist", default=False, type_="logical")
    l_conv_prog_group_1 = _get_var(config, "namelist:run_convection",
                     "l_conv_prog_group_1", default=False, type_="logical")
    l_conv_prog_group_2 = _get_var(config, "namelist:run_convection",
                     "l_conv_prog_group_2", default=False, type_="logical")
    l_conv_prog_group_3 = _get_var(config, "namelist:run_convection",
                     "l_conv_prog_group_3", default=False, type_="logical")
    l_conv_prog_precip = _get_var(config, "namelist:run_convection",
                     "l_conv_prog_precip", default=False, type_="logical")

    l_co2_interactive = False
    i_co2_opt = _get_var(config, "namelist:carbon_options", "i_co2_opt",
                      type_="integer")
    if i_co2_opt == 3:
        l_co2_interactive = True

    l_urban2t = _get_var(config, "namelist:urban_switches",
                     "l_urban2t", default=False, type_="logical")

    l_flake_model = _get_var(config, "namelist:jules_surface",
                     "l_flake_model", default=False, type_="logical")

    l_ctile = _get_var(config, "namelist:jules_sea_seaice", "l_ctile",
                      type_="logical")
    l_sea_alb_var_chl = _get_var(config, "namelist:jules_radiation",
                     "l_sea_alb_var_chl", default=False, type_="logical")

    l_rivers = _get_var(config, "namelist:run_rivers", "l_rivers",
                        default=False, type_="logical")
    l_inland = _get_var(config, "namelist:run_rivers", "l_inland",
                        default=False, type_="logical")

    nice_use = _get_var(config, "namelist:jules_sea_seaice", "nice_use", 
                        default=1,type_="integer")

    nice = _get_var(config, "namelist:jules_sea_seaice", "nice", default=1,
                        type_="integer")

    l_use_tpps_ozone = False
    can_model = _get_var(config, "namelist:jules_vegetation", "can_model",
                         default=False, type_="logical")
    l_use_cariolle = _get_var(config, "namelist:run_radiation",
                        "l_use_cariolle", default=False, type_="logical")
    l_endgame = _get_var(config, "namelist:run_dyn", "l_endgame",
                        default=False, type_="logical")

    # types are required by the cloud generator
    i_fsd = _get_var(config, "namelist:run_radiation", "i_fsd",
                     type_="integer")
    l_cca_dp_prog = False
    l_cca_md_prog = False
    l_cca_sh_prog = False
    ip_fsd_regime = 2
    ip_fsd_regime_smooth = 5
    ip_fsd_regime_no_sh = 3
    ip_fsd_regime_smooth_no_sh = 6

    if ((i_fsd == ip_fsd_regime) or (i_fsd == ip_fsd_regime_smooth)):
        l_cca_sh_prog = True
        l_cca_dp_prog = True
        l_cca_md_prog = True
    elif ((i_fsd == ip_fsd_regime_no_sh) or
          (i_fsd == ip_fsd_regime_smooth_no_sh)):
        l_cca_dp_prog = True
        l_cca_md_prog = True
    # Set radiation logicals based on namelist inputs - based on UM 
    # routine "check_run_radiation"
    i_rad_topography = _get_var(config, "namelist:run_radiation",
                           "i_rad_topography", default=0, type_="integer")
    l_use_grad_corr   = False
    l_orog_unfilt     = False
    if i_rad_topography == 0:
        l_use_grad_corr   = False
        l_orog_unfilt     = False
    elif i_rad_topography == 1:
        l_use_grad_corr   = False
        l_orog_unfilt     = False
    elif i_rad_topography == 2:
        l_use_grad_corr   = True
        l_orog_unfilt     = False
    elif i_rad_topography == 3:
        l_use_grad_corr   = False
        l_orog_unfilt     = False
    elif i_rad_topography == 4:
        l_use_grad_corr   = True
        l_orog_unfilt     = True

    l_use_sulpc_indirect_sw = _get_var(config, "namelist:run_radiation",
                     "l_use_sulpc_indirect_sw", default=False,
                      type_="logical")
    l_use_seasalt_direct = _get_var(config, "namelist:run_radiation",
                           "l_use_seasalt_direct", default=False,
                            type_="logical")
    l_use_seasalt_indirect = _get_var(config, "namelist:run_radiation",
                           "l_use_seasalt_indirect", default=False,
                            type_="logical")
    i_ozone_int = _get_var(config, "namelist:run_radiation",
                           "i_ozone_int", type_="integer")
    io3_trop_map_masscon = 5
    l_param_conv = _get_var(config, "namelist:run_convection", "l_param_conv",
                            default=False, type_="logical")
    l_gwd = _get_var(config, "namelist:run_gwd", "l_gwd", default=False,
                            type_="logical")
    l_use_ussp = _get_var(config, "namelist:run_gwd", "l_use_ussp",
                            default=False, type_="logical")
    l_cld_area = _get_var(config, "namelist:run_cloud", "l_cld_area",
                            default=False, type_="logical")
    l_rhcpt = _get_var(config, "namelist:run_cloud", "l_rhcpt",
                            default=False, type_="logical")
    l_use_seasalt_pm = _get_var(config, "namelist:run_aerosol",
                            "l_use_seasalt_pm", default=False,
                            type_="logical")

    # tracers and ukca
    tracer_a = _get_tracer_a(config, a_max_trvars)

    tracer_lbc = [0 for i in range(a_max_trvars)]
    l_free_tracer_lbc = _get_var(config, "namelist:run_free_tracers",
                         "l_free_tracer_lbc", default=False, type_="logical")
    if l_free_tracer_lbc:
        i_free_tracer_lbc = _get_var(config, "namelist:run_free_tracers",
                         "i_free_tracer_lbc", array=True, type_="integer")

    tc_lbc_ukca = [0 for i in range(a_max_trvars)]
    l_ukca = _get_var(config, "namelist:run_ukca", "l_ukca", default=False,
                               type_="logical")
    if l_ukca and nsec == 37:
        tc_lbc_ukca = _get_var(config, "namelist:run_ukca", "tc_lbc_ukca",
                               array=True, type_="integer")

    l_ukca_chem_aero = _get_var(config, "namelist:run_ukca",
                         "l_ukca_chem_aero", default=False, type_="logical")

    l_ukca_mode = _get_var(config, "namelist:run_ukca", "l_ukca_mode",
                          default=False, type_="logical")

    l_ukca_new_emiss = _get_var(config, "namelist:run_ukca", "l_ukca_new_emiss",
                                default=False, type_="logical")
    
    # Stochastic physics A35
    l_skeb2 = _get_var(config, "namelist:run_stochastic", "l_skeb2",
               default=False, type_="logical")
    l_spt = _get_var(config, "namelist:run_stochastic", "l_spt",
               default=False, type_="logical")
    
    
    # Var reconfiguration now is not restricted to primary fields,
    # therefore need to perform on all sections
    var_recon = _get_var(config, "namelist:recon", "var_recon",
                         default=False, type_="logical")
    if var_recon and (n17 != 1):
        l_mask = False
        msg = _form_msg("n17", n17, "RCF is True and n17 != 1")

    # Atmosphere primary fields
    if (nsec == 0 or nsec == 31 or nsec == 32 or  nsec == 33 or
        nsec == 36 or nsec == 37):
        if sum_iopn != 0:
            if nsec == 33 or nsec == 36 or nsec == 37:
                n2n1 = int(iopn[30 - 3:])

            if (n2n1 == 99 and nsec != 33 and nsec != 36 and
                               nsec != 37):
                l_mask = False
                msg = _form_msg("n2n1", n2n1, "sections 33,36,37 not selected")
            elif nsec == 33 or nsec == 36:
                if n2n1 > 0 and n2n1 <= a_max_trvars:
                    if ((nsec == 33 and not (tracer_a[n2n1 - 1])) or
                        (nsec == 36 and i_free_tracer_lbc[n2n1 - 1] == 0)):
                        l_mask = False
                        msg = _form_msg("n2n1", n2n1, "check tracers")
            elif nsec == 37:
                if n2n1 > 0 and n2n1 <= a_max_ukcavars:
                    if (tc_lbc_ukca[n2n1 - 1] == 0):
                        l_mask = False
                        msg = _form_msg("n2n1", n2n1, "check tracers")
            elif n30 == 0:
                # n3 = 1 not to be used because of tracers
                # n3 = 2 not to be used because of tracers
                if n3 == 5 and not l_top:
                    # topmodel hydrology
                    l_mask = False
                    msg = _form_msg("n3", n3, "topmodel hydrology")

                elif n4 == 1 and not l_use_biogenic:
                    # biogenic aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_biogenic")
                elif n4 == 2 and not l_use_arclbiom:
                    # biomass burning aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arclbiom")
                elif n4 == 3 and not l_use_arclblck:
                    # black carbon aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arclblck")
                elif n4 == 4 and not l_use_arclsslt:
                    # sea salt aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "sea salt aerosol")
                elif n4 == 5 and not l_use_arclsulp:
                    # sulphate aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arclsulp")
                elif n4 == 6 and not l_use_arcldust:
                    # dust aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arcldust")
                elif n4 == 7 and not l_use_arclocff:
                    # organic carbon fossil fuel
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arclocff")
                elif n4 == 8 and not l_use_arcldlta:
                    # delta aerosol
                    l_mask = False
                    msg = _form_msg("n4", n4, "not l_use_arcldlta")
                elif n4 > 8:
                    # 9 is wrong option code
                    l_mask = False
                    msg = _form_msg("n4", n4, "wrong option code")
                elif n5 == 1 and formdrag == 0:
                    # orographic roughness
                    l_mask = False
                    msg = _form_msg("n5", n5, "formdrag == 0")
                elif n5 == 2 and (i_gwd_vn != 0 and
                                  i_gwd_vn != 4 and
                                  i_gwd_vn != 5):
                    # orographic gradient
                    l_mask = False
                    msg = _form_msg("n5", n5, "orographic gradient")
                elif n5 == 3 and not l_use_grad_corr:
                    # gradient correction for SW radiation
                    l_mask = False
                    msg = _form_msg("n5", n5, "not l_use_grad_corr")
                elif n5 == 4 and not l_orog_unfilt:
                    # unfiltered orography for horizon angles
                    l_mask = False
                    msg = _form_msg("n5", n5, "not l_orog_unfilt")
                elif n6 == 1 and h_global == 1:
                    # limited area boundary conditions
                    l_mask = False
                    msg = _form_msg("n6", n6, "LBC conditions")
                elif n7 == 1 and not l_oasis:
                    # OASIS coupling to ocean model
                    l_mask = False
                    msg = _form_msg("n7", n7, "not OASIS coupling")
                elif n7 == 2 or n7 == 7:
                    # other coupling fields currently excluded
                    l_mask = False
                    msg = _form_msg("n7", n7,
                           "other coupling fields currently excluded")
                elif n7 == 3 and not (l_oasis and l_oasis_icecalve):
                    # oasis iceberg calving
                    l_mask = False
                    msg = _form_msg("n7", n7,
                           "not l_oasis and l_oasis_icecalve")
                elif n8 == 1 and not l_sstanom:
                    # SST anomaly
                    l_mask = False
                    msg = _form_msg("n8", n8, "not l_sstanom")
                elif n8 == 2 and iscrntdiag != 2:
                    # diagnosis of screen temperature
                    l_mask = False
                    msg = _form_msg("n8", n8, "iscrntdiag != 2")
                elif n8 == 3 and isrfexcnvgust == 0:
                    # convective downdraughts on surface exchange
                    l_mask = False
                    msg = _form_msg("n8", n8,
                        "convective downdraughts on surface exchange")
                elif n8 == 4 and not l_murk:
                    # total aerosol (murk) for visibility
                    l_mask = False
                    msg = _form_msg("n8", n8,
                           "total aerosol (murk) for visibility")
                elif n8 == 5 and not l_murk_source:
                    # total aerosol emissions
                    l_mask = False
                    msg = _form_msg("n8", n8, "not l_murk_source")
                elif (n8 == 6 and nsmax == 0 and 
                      not (l_snow_albedo or l_embedded_snow)):
                    # snow albedo
                    l_mask = False
                    msg = _form_msg("n8", n8,
                           "nsmax == 0 and not l_snow_albedo")
                elif n8 == 7 and i_bl_vn != 1:
                    # tke closure
                    l_mask = False
                    msg = _form_msg("n8", n8, "tke closure")
                elif n8 == 8 and not l_emcorr:
                    # energy adjustment scheme
                    l_mask = False
                    msg = _form_msg("n8", n8, "not l_emcorr")
                elif n8 == 9 and not l_use_electric:
                    # electric scheme is in use
                    l_mask = False
                    msg = _form_msg("n8", n8, "electric scheme is in use")
                # n10n9 is used for all CLASSIC aerosol prognostics
                # Sulphur cycle (1-19)
                elif n10n9 == 1 and not l_sulpc_so2:
                    # sulphur dioxide cycle
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "sulphur dioxide cycle")
                elif ( n10n9 == 2 and ( not l_sulpc_so2 or not l_so2_surfem )
                             and ( not l_ukca_chem_aero or l_ukca_new_emiss) ):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "surface SO2 emissions")
                elif ( n10n9 == 3 and ( not l_sulpc_so2 or not l_so2_hilem ) 
                             and ( not l_ukca_chem_aero or l_ukca_new_emiss) ):
                    # high level SO2 emissions
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "high level SO2 emissions")
                elif ( n10n9 == 4 and ( not l_sulpc_so2 or not l_so2_natem )
                             and ( not l_ukca_chem_aero or l_ukca_new_emiss) ):
                    # natural SO2 emissions
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "not natural SO2 emissions")
                elif ( n10n9 == 5 and (not l_sulpc_so2 or
                                     not l_sulpc_dms) ):
                    # dimethyl sulphide in SO2 cycle
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "dimethyl sulphide in SO2 cycle")
                elif ( n10n9 == 6 and ( not l_sulpc_so2 or 
                                        not l_sulpc_dms or
                                        not l_dms_em ) 
                             and ( not l_ukca_chem_aero or l_ukca_new_emiss) ):
                    # dimethyl sulphide emissions
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "dimethyl sulphide emissions")
                elif ( n10n9 == 7 and (not l_sulpc_so2 or
                                     l_sulpc_online_oxidants or
                                     not l_sulpc_ozone) ):
                    # offline ozone oxidant in SO2 cycle
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "offline ozone oxidant in SO2 cycle")
                elif ( n10n9 == 8 and (not l_sulpc_so2 or
                                     not l_sulpc_ozone or
                                     not l_sulpc_nh3) ):
                    # ozone and ammonia in SO2 cycle
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "ozone and ammonia in SO2 cycle")
                elif ( n10n9 == 9 and ( not l_sulpc_so2 or
                                        not l_sulpc_ozone or
                                        not l_sulpc_nh3 or
                                        not l_nh3_em ) 
                             and ( not l_ukca_chem_aero or l_ukca_new_emiss) ):
                    # ammonia emissions and O3 in SO2 cycle
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "ammonia emissions and O3 in SO2 cycle")
                elif ( n10n9 == 10 and (not l_sulpc_so2 or
                                      l_sulpc_online_oxidants) ):
                    # offline oxidants, not ozone
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "offline oxidants, not ozone")
                elif ( n10n9 == 11 and ( not l_sulpc_so2 or
                                         not l_sulpc_dms or
                                         not l_dms_em ) and
                                         not l_ukca_chem_aero ):
                    # dimethyl sulphide sea water concentration
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "dimethyl sulphide sea water concentration")
                # Soot cycle (21 - 23)
                elif n10n9 == 21 and not l_soot:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "soot cycle")
                elif n10n9 == 22 and (not l_soot or not l_soot_surem):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "soot cycle")
                elif n10n9 == 23 and (not l_soot or not l_soot_hilem):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "soot cycle")
                # Biomass (24 - 26)
                elif n10n9 == 24 and not l_biomass:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "biomass")
                elif ( n10n9 == 25 and (not l_biomass or
                                      not l_bmass_surem) ):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "biomass")
                elif ( n10n9 == 26 and (not l_biomass or
                                      not l_bmass_surem) ):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "biomass")
                # 2 bin and 6 bin Mineral dust
                elif n10n9 == 27 and not l_dust:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "2 bin and 6 bin Mineral dust")
                elif n10n9 == 28 and not l_dust and not l_dust_diag:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "2 bin and 6 bin Mineral dust")
                # Nitrate (31)
                elif n10n9 == 31 and not l_nitrate:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "nitrate")
                # OCFF (35-37)
                elif n10n9 == 35 and not l_ocff:
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "OCFF")
                elif n10n9 == 36 and (not l_ocff or not l_ocff_surem):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "OCFF")
                elif n10n9 == 37 and (not l_ocff or not l_ocff_hilem):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9, "OCFF")
                # 6 bin only Mineral dust
                elif n10n9 == 38 and (l_twobin_dust or not l_dust):
                    l_mask = False
                    msg = _form_msg("n10n9", n10n9,
                           "6 bin only Mineral dust")
                # End of classic aerosol section
                elif n11 == 1:
                    # basic vegetation scheme, no longer supported
                    l_mask = False
                    msg = _form_msg("n11", n11,
                       "basic vegetation scheme, no longer supported")
                elif n11 == 2 and False:
                    # fractional vegetation scheme
                    l_mask = False
                    msg = _form_msg("n11", n11,
                           "fractional vegetation scheme")
                elif n11 == 3 and (not l_triffid):
                    l_mask = False
                    msg = _form_msg("n11", n11,
                           "not l_triffid")
                elif n11 == 4 and ((not l_albedo_obs) or l_spec_albedo):
                    # SW albedo_obs
                    l_mask = False
                    msg = _form_msg("n11", n11, "SW albedo_obs")
                elif n11 == 5 and not (l_albedo_obs and l_spec_albedo):
                # VIS and NIR albedo_obs
                    l_mask = False
                    msg = _form_msg("n11", n11,
                           "VIS and NIR albedo_obs")
                elif n11 == 6 and not (l_aggregate and
                                      (i_aggregate_opt == 1)):
                    # No separate prognostic for thermal roughness
                    l_mask = False
                    msg = _form_msg("n11", n11,
                       "No separate prognostic for thermal roughness")
                elif n11 == 7 and not l_vary_z0m_soil:
                    # No prognostic bare soil momentum roughness
                    l_mask = False
                    msg = _form_msg("n11", n11,
                       "No prognostic for bare soil momentum roughness")
                elif n12 == 3 and not l_mcr_qcf2:
                    # QCF2 is prognostic
                    l_mask = False
                    msg = _form_msg("n12", n12, "QCF2 is prognostic")
                elif n12 == 4 and not l_mcr_qrain:
                    # QRAIN is prognostic
                    l_mask = False
                    msg = _form_msg("n12", n12, "QRAIN is prognostic")
                elif n12 == 5 and not l_mcr_qgraup:
                    # QGRAUP is prognostic
                    l_mask = False
                    msg = _form_msg("n12", n12, "QGRAUP is prognostic")
                elif n12 == 6 and not l_pc2:
                    # PC2 clod fraction boundary values out (secn.32)
                    l_mask = False
                    msg = _form_msg("n12", n12,
                           "PC2 cloud fraction boundary values out")
                elif n12 == 7 and not l_subgrid_qcl_mp:
                    l_mask = False
                    msg = _form_msg("n12", n12,
                           "Turbulent mixed-phase scheme is switched off")
#                elif n12 == 8 and not l_casim:
#                    l_mask = False
#                    msg = _form_msg("n12", n12,
#                           "CASIM microphysics is switched off")
                elif n13 == 1 and l_3d_cca:
                    # convective cloud amount is 2D
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "convective cloud amount is 2D")
                elif n13 == 2 and not l_3d_cca:
                    # convective cloud amount is 3D
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "convective cloud amount is 3D")
                elif n13 == 3 and not l_ccrad:
                    # CCRad scheme
                    l_mask = False
                    msg = _form_msg("n13", n13, "CCRad scheme")
                elif n13 == 5 and not l_conv_hist:
                    # fields for convection history
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "fields for convection history")
                elif n13 == 6 and not l_conv_prog_group_1:
                    # Convection experimental prognostic fields group 1
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "Convection experimental prognostic fields group 1")
                elif n13 == 7 and not l_conv_prog_group_2:
                    # Convection experimental prognostic fields group 2
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "Convection experimental prognostic fields group 2")
                elif n13 == 8 and not l_conv_prog_group_3:
                    # Convection experimental prognostic fields group 3
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "Convection experimental prognostic fields group 3")
                elif n13 == 9 and not l_conv_prog_precip:
                    # Convection prognostic recent precipitation field
                    l_mask = False
                    msg = _form_msg("n13", n13,
                           "Convection recent precipitation prognostic field")
                elif n15 == 3 and not l_co2_interactive:
                    # carbon cycle scheme
                    l_mask = False
                    msg = _form_msg("n15", n15, "carbon cycle scheme")
                elif n16 == 2 and nsmax == 0:
                    # JULES snow scheme with multiple snow layers
                    l_mask = False
                    msg = _form_msg("n16", n16,
                           "JULES snow scheme with multiple snow layers")
                elif n16 == 3 and not (l_snow_albedo or l_embedded_snow):
                    # snow soot
                    l_mask = False
                    msg = _form_msg("n16", n16, "snow soot")
                elif n16 == 4 and not l_urban2t:
                    # URBAN-2T schemes including MORUSES
                    l_mask = False
                    msg = _form_msg("n16", n16,
                           "URBAN-2T schemes including MORUSES")
                elif n16 == 5 and not l_flake_model:
                    # FLake lake scheme
                    l_mask = False
                    msg = _form_msg("n16", n16, "FLake lake scheme")
                # n17 is left out here, as it is for all sections not
                # just prognostics
                elif n18 == 1 and not l_ctile:
                    # coastal tiling scheme
                    l_mask = False
                    msg = _form_msg("n18", n18,
                           "coastal tiling scheme")
                elif n18 == 2 and not l_sea_alb_var_chl:
                    # open sea albedo has variable chlorophyll content
                    l_mask = False
                    msg = _form_msg("n18", n18,
                    "open sea albedo has variable chlorophyll content")
                elif n18 == 3 and not l_rivers:
                    # river routing scheme    # Atmosphere primary fields
                    l_mask = False
                    msg = _form_msg("n18", n18,
                           "river routing scheme")
                elif n18 == 4 and not l_inland:
                    # inland re-routing scheme
                    l_mask = False
                    msg = _form_msg("n18", n18,
                           "inland re-routing scheme")
                elif n18 == 6 and (nice_use > 1):
                    # single sea ice category
                    l_mask = False
                    msg = _form_msg("n18", n18,
                           "single sea ice category")
                elif n18 == 7 and (nice == 1):
                    # sea ice categories
                    l_mask = False
                    msg = _form_msg("n18", n18, "sea ice categories")
                elif n18 == 8 and (nice_use == 1):
                    # sea ice categories used fully
                    l_mask = False
                    msg = _form_msg("n18", n18,
                           "sea ice categories used fully")
                elif n18 == 9 and not l_sice_multilayers:
                    # multilayer sea ice scheme
                    l_mask = False
                    msg = _form_msg("n18", n18, "l_sice_multilayers")
                elif n19 == 1 and not l_use_tpps_ozone:
                    # tropopause ozone scheme
                    l_mask = False
                    msg = _form_msg("n19", n19,
                           "tropopause ozone scheme")
                elif n20 == 1 and can_model != 4 and nsmax == 0:
                    # snow canopy scheme
                    l_mask = False
                    msg = _form_msg("n20", n20, "snow canopy scheme")
                elif n20 == 2 and not l_sice_meltponds_cice:
                    # snow canopy scheme
                    l_mask = False
                    msg = _form_msg("n20", n20, "sea ice meltpond albedo scheme")
                elif n20 == 3 and not l_saldep_freeze:
                    # snow canopy scheme
                    l_mask = False
                    msg = _form_msg("n20", n20, 
                                  "salinity-dependent sea surface freezing temp")
                elif n21 == 1 and not l_cca_dp_prog:
                    # cca_dp used in cloud generator
                    l_mask = False
                    msg = _form_msg("n21", n21,
                           "cca_dp used in cloud generator")
                elif n21 == 2 and not l_cca_md_prog:
                    # cca_md used in cloud generator
                    l_mask = False
                    msg = _form_msg("n21", n21,
                           "cca_md used in cloud generator")
                elif n21 == 3 and not l_cca_sh_prog:
                    # cca_dp used in cloud generator
                    l_mask = False
                    msg = _form_msg("n21", n21,
                           "cca_dp used in cloud generator")
                elif n25 == 3:
                    # Direct PAR prognostic not currently used
                    # by any scheme
                    l_mask = False
                    msg = _form_msg("n25", n25,
                       "Direct PAR prognostic not used by any scheme")
                elif n28 == 1 and not l_use_cariolle:
                    # cariolle ozone scheme
                    l_mask = False
                    msg = _form_msg("n28", n28,
                           "cariolle ozone scheme")
                elif n29 == 1 and not l_endgame:
                    # Disable ENDGame prognostics in ND run
                    l_mask = False
                    msg = _form_msg("n29", n29,
                           "Disable ENDGame prognostics in ND run")
                elif n30 == 1:
                    # Do nothing for now
                    # Can be used for a new set of option codes with n30=1
                    # when those with n30=0 are fully used up
                    l_mask = False
                    msg = _form_msg("n30", n30, "")
            # End if n30
        # End if SUM_IOPN
    # End if ISEC
    # End of atmos prognostic block

    # UKCA
    if nsec == 34 or nsec == 51 or nsec == 50 or nsec == 52:
        l_mask, msg = _tstmsk_ukca(config, n1, n2, n3, n4, n5, n6, n7,
                                   n8, n9, n10, n11, n12, n13, n14, n15,
                                   n16, n17, n18, n19, n20, n21, n22,
                                   n23, n24, n25, n26, n27, n28, n29,
                                   n30, l_ukca, l_ukca_mode, sum_iopn)

    # Atmos Diagnostics
    # Short wave radiation
    if nsec == 1:
        if sum_iopn != 0:
            if n1 == 1 and h_global != 1:
                l_mask = False
                msg = _form_msg("n1", n1, "h_global != 1")
            elif n4 == 1 and not l_use_sulpc_indirect_sw:
                l_mask = False
                msg = _form_msg("n4", n4, "not l_use_sulpc_indirect_sw")
            elif n5 == 1 and not (l_use_seasalt_direct or
                                  l_use_seasalt_indirect):
                l_mask = False
                msg = _form_msg("n5", n5,
                    "not(l_use_seasalt_direct or l_use_seasalt_indirect)")
            elif n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "not l_pc2")
    # Long wave radiation
    elif nsec == 2:
        if sum_iopn != 0:
            if n1 == 1 and (i_ozone_int != io3_trop_map_masscon):
                l_mask = False
                msg = _form_msg("n1", n1,
                       "i_ozone_int != io3_trop_map_masscon")
            if n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "l_pc2")
    # Boundary layer
    elif nsec == 3:
        if sum_iopn != 0:
            if n1 == 1 and formdrag == 0:
                l_mask = False
                msg = _form_msg("n1", n1, "formdrag == 0")
            if n2 == 1 and not l_sulpc_so2:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_sulpc_so2")
            elif n2 == 2 and not l_sulpc_nh3:
                l_mask = False
                msg = _form_msg("n2", n2, "l_sulpc_nh3")
            elif n2 == 3 and not l_soot:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_soot")
            elif n2 == 4 and not l_biomass:
                l_mask = False
                msg = _form_msg("n4", n4, "not l_biomass")
            elif n2 == 5 and not l_dust:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_dust")
            elif n2 == 6 and not l_ocff:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_ocff")
            elif n2 == 7 and not l_nitrate:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_nitrate")
            elif n2 == 8 and not l_dust and not l_dust_diag:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_dust and not l_dust_diag")
            if n3 == 1 and not l_co2_interactive:
                l_mask = False
                msg = _form_msg("n3", n3, "not l_co2_interactive")
            elif n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "l_pc2")
            if n4 == 1 and nice == 1:
                l_mask = False
                msg = _form_msg("n4", n4, "nice == 1")
            elif n4 == 2 and nice_use == 1:
                l_mask = False
                msg = _form_msg("n4", n4, "nice_use == 1")
            # 2 and 6 bin dust fields
            if n7 == 1 and not l_dust and not l_dust_diag :
                l_mask = False
                msg = _form_msg("n7", n7, "l_dust")
            # 6 bin dust only fields
            elif n7 == 2 and (l_twobin_dust or (not l_dust and 
                  not l_dust_diag)):
                l_mask = False
                msg = _form_msg("n7", n7, "l_twobin_dust or not l_dust")
    # Large-scale precipitation
    elif nsec == 4:
        if sum_iopn != 0:
            if n2 == 1 and not l_sulpc_so2:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_sulpc_so2")
            elif n2 == 2 and not l_sulpc_nh3:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_sulpc_nh3")
            elif n2 == 3 and not l_soot:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_soot")
            elif n2 == 4 and not l_biomass:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_biomass")
            elif n2 == 5 and not l_dust:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_dust")
            elif n2 == 6 and not l_ocff:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_ocff")
            elif n2 == 7 and not l_nitrate:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_nitrate")
            if n5 == 1 and not l_subgrid_qcl_mp:
                msg = _form_msg("n5", n5, "not l_subgrid_qcl_mp")
            if n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "l_pc2")
            # 2 and 6 bin dust fields
            if n7 == 1 and not l_dust:
                l_mask = False
                msg = _form_msg("n7", n7, "not l_dust")
            # 6 bin dust only fields
            elif n7 == 2 and (l_twobin_dust or not l_dust):
                l_mask = False
                msg = _form_msg("n7", n7, "l_twobin_dust or not l_dust")
            # CASIM microphysics
#            if n8 == 1 and not l_casim:
#                l_mask = False
#                msg = _form_msg("n8", n8, "not l_casim")
    # Convection
    elif nsec == 5:
        if sum_iopn != 0:
            if n2 == 1 and not l_sulpc_so2:
                l_mask = False
                msg = _form_msg("n2", n2, "l_sulpc_so2")
            elif n2 == 2 and not l_sulpc_nh3:
                l_mask = False
                msg = _form_msg("n2", n2, "l_sulpc_nh3")
            elif n2 == 3 and not l_soot:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_soot")
            elif n2 == 4 and not l_biomass:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_biomass")
            elif n2 == 5 and not l_dust:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_dust")
            elif n2 == 6 and not l_ocff:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_ocff")
            elif n2 == 7 and not l_nitrate:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_nitrate")
            elif n3 == 1 and l_3d_cca:
                l_mask = False
                msg = _form_msg("n3", n3, "l_3d_cca")
            elif n3 == 1 and not l_3d_cca:
                l_mask = False
                msg = _form_msg("n3", n3, "not l_3d_cca")
            if n6 == 1 and not l_pc2:
                l_maskk = False
                msg = _form_msg("n6", n6, "not l_pc2")
            # 2 and 6 bin dust fields
            if n7 == 1 and not l_dust:
                l_mask = False
                msg = _form_msg("n7", n7, "not l_dust")
            # 6 bin dust only fields
            elif n7 == 2 and (l_twobin_dust or not l_dust):
                l_mask = False
                msg = _form_msg("n7", n7,
                       "l_twobin_dust or not l_dust)")
            if n4 != 1 and not l_param_conv:
                l_mask = False
                msg = _form_msg("n4", n4, "n4 != 1 and not l_param_conv")
    # Gravity Wave Drag parametrization
    elif nsec == 6:
        if sum_iopn != 0:
            if n2 == 1 and not l_gwd:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_gwd")
            elif n3 == 1 and not l_use_ussp:
                l_mask = False
                msg = _form_msg("n3", n3, "not l_use_ussp")
    # Hydrology
    elif nsec == 8:
        if sum_iopn != 0:
            if n1 == 1 and not l_top:
                l_mask = False
                msg = _form_msg("n1", n1, "not l_top")
            elif n22 == 1 and not l_rivers:
                l_mask = False
                msg = _form_msg("n22", n22, "not l_rivers")
            elif n22 == 2 and not l_inland:
                l_mask = False
                msg = _form_msg("n22", n22, "not l_inland")
    # Cloud parametrization
    elif nsec == 9:
        if sum_iopn != 0:
            if n2 == 1 and not l_cld_area:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_cld_area")
            elif n3 == 1 and not l_rhcpt:
                l_mask = False
                msg = _form_msg("n3", n3, "not l_rhcpt")
            elif n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "not l_pc2")
    # Dynamics Advection
    elif nsec == 12:
        if sum_iopn != 0:
            if n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "not l_pc2")
    # Extra physics
    elif nsec == 16:
        if sum_iopn != 0:
            if n2n1 != 0 and not tracer_a[n2n1 - 1]:
                l_mask = False
                msg = _form_msg("n2n1", n2n1, "not tracer_a[n2n1]")
            if n6 == 1 and not l_pc2:
                l_mask = False
                msg = _form_msg("n6", n6, "not l_pc2")
    # CLASSIC Aerosol section
    elif nsec == 17:
        if sum_iopn != 0:
            if n1 == 1 and not l_sulpc_so2:
                # Sulphur cycle diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_sulpc_so2")
            elif n1 == 2 and not l_soot:
                # Soot diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_soot")
            elif n1 == 3 and not l_biomass:
                # Biomass aerosol diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_biomass")
            elif n1 == 4 and not l_dust:
                # Dust aerosol diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_dust")
            elif n1 == 5 and not l_ocff:
                # OCFF aerosol diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_ocff")
            elif n1 == 6 and not l_use_biogenic:
                # SOA aerosol diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_use_biogenic")
            elif n1 == 7 and not l_use_seasalt_pm:
                # Sea-salt PM diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_use_seasalt_pm")
            elif n1 == 8 and not l_nitrate:
                # Nitrate aerosol diagnostics
                l_mask = False
                msg = _form_msg("n1", n1, "not l_nitrate")
            elif n1 == 9 and not (l_sulpc_so2 or l_soot or l_biomass or
                                  l_dust or l_ocff or l_use_biogenic or
                                  l_use_seasalt_pm or l_nitrate):
                l_mask = False
                msg = _form_msg("n1", n1, "not any of aerosol scheme")
            if n2 == 1 and not l_sulpc_dms:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_sulpc_dms")
            elif n2 == 2 and not l_sulpc_ozone:
                l_mask = False
                msg = _form_msg("n2", n2, "not l_sulpc_ozone")
    # Data assimilation
    elif nsec == 18:
        if sum_iopn != 0:
            # Do nothing
            msg = _form_msg("sum_iopn", sum_iopn, "data assimilation")

    elif nsec >= 1 and nsec <= 20:
        # but not sec 1,3 18
        if sum_iopn != 0:
            l_mask = False
            msg = _form_msg("sum_iopn", sum_iopn,
                   "atmos climate mean diagnostics redundant")
    # Thunderstorm electrification
    elif nsec == 21:
        if not l_use_electric:
            l_mask = False
            msg = _form_msg("nsec", nsec, "not l_use_electric")
        elif sum_iopn != 0:
            if n2 == 1 and electric_method != 2:
                l_mask = False
                msg = _form_msg("n2", n2, "electric_method != 2")
    elif nsec >= 22 and nsec <= 24:
    # Atmos climate mean diagnostics - redundant
        l_mask = False
        msg = _form_msg("nsec", nsec,
              "atmos climate mean diagnostics redundant")
    # River Routing Diagnostics
    elif nsec == 26:
        if sum_iopn != 0:
            if n22 == 1 and not l_rivers:
                # River routing switched off
                l_mask = False
                msg = _form_msg("n22", n22, "not l_rivers")
            elif n22 == 2 and not l_inland:
                # Inland re-routing switched off
                l_mask = False
                msg = _form_msg("n22", n22, "not l_inland")
    # FV-TRACK diagnostics
    elif nsec == 30:
        if n1 == 1 and h_global != 1:
            l_mask = False
            msg = _form_msg("n1", n1,
            "FV-TRACK diagnostic only available for global model")                
    # Stochastic physics            
    elif nsec == 35:
      if sum_iopn != 0:
        if n1 == 1 and not l_skeb2:
          l_mask = False
          msg = _form_msg("n1", n1,
          "SKEB2 is not switched on")
        elif n1 == 2 and not l_spt:
          l_mask = False
          msg = _form_msg("n1", n1,
          "SPT is not switched on")
    # End of atmos diagnostic block

    # Check space code
    if l_mask:
        ispace = exppxi.get(isec, item, "space")
        if ispace == 3 or ispace == 5:
            l_mask = False
            msg = _form_msg("ispace", ispace, "space code")

    rc_tu = (l_mask, msg)
    return rc_tu


def _get_hvers(config, n_internal_model_max, nsectp=99):
    """ Treat each code section to provide a version number for use
        by tstmsk, based on i_<section name>_vn as previous IFDEFs
        became obsolete
    """

    h_vers = [[None for j in range(nsectp+1)]
                  for i in range(n_internal_model_max)]
    atmos_im = 1
    # prognostics section: to be compatible with mask version
    h_vers[atmos_im - 1][0] = 1

    # A01 and A02 Radiation SW LW only version 3 available
    h_vers[atmos_im - 1][1] = 3
    h_vers[atmos_im - 1][2] = 3

    # A03 BL has multiple versions
    i_bl_vn = _get_var(config, "namelist:run_bl", "i_bl_vn", type_="integer")
    if i_bl_vn == 2 or i_bl_vn == 3:
        h_vers[atmos_im - 1][3] = 9
    else:
        h_vers[atmos_im - 1][3] = i_bl_vn

    # A04 LSP has now two options, version 4 (CASIM) or
    # version 3 (Wilson and Ballard, 1999).
    l_casim = False
    if l_casim:
        h_vers[atmos_im - 1][4] = 4
    else:
        h_vers[atmos_im - 1][4] = 3

    # A05 Convection has multiple versions 0A, 4A, 5A, 6A
    i_convection_vn = _get_var(config, "namelist:run_convection",
                               "i_convection_vn", type_="integer")
    h_vers[atmos_im - 1][5] = i_convection_vn

    # A06 GWD has multiple sections 4A and 5A
    i_gwd_vn = _get_var(config, "namelist:run_gwd", "i_gwd_vn",
                        type_="integer")
    h_vers[atmos_im - 1][6] = i_gwd_vn

    # A08 Land Surface used only with hydrology
    l_hydrology = _get_var(config, "namelist:jules_hydrology", "l_hydrology",
                           default=False, type_="logical")
    if l_hydrology:
        h_vers[atmos_im - 1][8] = 8

    # A09 Large Scale Cloud only version 2 available
    h_vers[atmos_im - 1][9] = 2

    # A10 Dynamics Solver only valid for new Dynamics 2A and 2B
    # For End Game diagnostics in section 10 are not available
    l_endgame = _get_var(config, "namelist:run_dyn", "l_endgame",
                          default=False, type_="logical")
    if l_endgame:
        h_vers[atmos_im - 1][10] = 4
    else:
        h_vers[atmos_im - 1][10] = 2

    # A11 For Tracer advection there are no diags, so could be anything
    h_vers[atmos_im - 1][11] = 0

    # A12 Dynamics advection diagnostics for New Dynamics
    # Not clear which are valid for Enf Game; needs to be revisited
    h_vers[atmos_im - 1][12] = 2

    # A13 Diffusion and Filtering too complicated at present, assume 2A or 2B
    h_vers[atmos_im - 1][13] = 2

    # A14 Energy Correction single version
    l_emcorr = _get_var(config, "namelist:run_eng_corr", "l_emcorr",
                        default=False, type_="logical")
    if l_emcorr:
        h_vers[atmos_im - 1][14] = 1

    # A15 Dynamics diagnostics assume always available
    h_vers[atmos_im - 1][15] = 1

    # A16 Physics diagnostics assume always available
    h_vers[atmos_im - 1][16] = 1

    # A17 Aerosols very complex to follow if diags available or not
    l_soot = _get_var(config, "namelist:run_aerosol", "l_soot",
                      default=False, type_="logical")
    l_sulpc_so2 = _get_var(config, "namelist:run_aerosol", "l_sulpc_so2",
                      default=False, type_="logical")
    l_ocff = _get_var(config, "namelist:run_aerosol", "l_ocff",
                      default=False, type_="logical")
    i_dust = _get_var(config, "namelist:run_dust", "i_dust",
                       default=0, type_="integer")
    l_biomass = _get_var(config, "namelist:run_aerosol", "l_biomass",
                      default=False, type_="logical")
    l_nitrate = _get_var(config, "namelist:run_aerosol", "l_nitrate",
                      default=False, type_="logical")
    l_triffid = _get_var(config, "namelist:jules_vegetation",
                      "l_triffid", type_="logical")
    l_aero = False
    if (l_soot or l_biomass or (i_dust != 0 and i_dust is not None) or
                                l_sulpc_so2 or l_ocff or l_nitrate):
        l_aero = True
    if l_aero:
        h_vers[atmos_im - 1][17] = 2

    # A18 Data assimilation single version
    l_iau = _get_var(config, "namelist:iau_nl", "l_iau",
             default=False, type_="logical")
    if l_iau:
        h_vers[atmos_im - 1][18] = 2

    # A19 Veg distribution
    i_veg_vn = 2 if l_triffid else 1
    h_vers[atmos_im - 1][19] = i_veg_vn

    # A20 PWS diagnostics assume always wanted
    h_vers[atmos_im - 1][20] = 1

    # A21 Thunderstorm Electrification
    l_use_electric = _get_var(config, "namelist:run_electric",
                         "l_use_electric", default=False, type_="logical")
    if l_use_electric:
        h_vers[atmos_im - 1][21] = 1

    # A26 River routing
    l_rivers = _get_var(config, "namelist:run_rivers",
                         "l_rivers", default=False, type_="logical")
    if l_rivers:
        i_river_vn = _get_var(config, "namelist:run_rivers",
                         "i_river_vn", type_="integer")
        h_vers[atmos_im - 1][26] = i_river_vn


    # A30 Climate diagnostics assume always wanted
    h_vers[atmos_im - 1][30] = 1

    # A31 LBC INPUT
    h_vers[atmos_im - 1][31] = 1

    # A33 Free Tracers  set as available should someone use them
    h_vers[atmos_im - 1][33] = 1

    # A34, A37, A50: UKCA, UKCA LBCs and UKCA ASAD
    l_ukca = _get_var(config, "namelist:run_ukca", "l_ukca",
               default=False, type_="logical")
    if l_ukca:
        h_vers[atmos_im - 1][34] = 1
        h_vers[atmos_im - 1][37] = 1
        h_vers[atmos_im - 1][50] = 1

    # Stochastic physics A35 (triggered by each schemes separately)
    h_vers[atmos_im - 1][35] = 1

    # A36 Atmos tracer LBCs
    h_vers[atmos_im - 1][36] = 1

    # UKCA Aerosols diagnostics - on if GLOMAP is on.
    l_ukca_mode = _get_var(config, "namelist:run_ukca", "l_ukca_mode",
                      default=False, type_="logical")
    if l_ukca_mode:
        h_vers[atmos_im - 1][38] = 1

    # A39 Nudging scheme
    l_nudging = _get_var(config, "namelist:run_nudging", "l_nudging",
                  default=False, type_="logical")
    if l_nudging:
        h_vers[atmos_im - 1][39] = 1

    # A51 UKCA diagnostics on pressure levels  - on if 
    if l_ukca:
        l_ukca_chem_plev = _get_var(config, "namelist:run_ukca",
                  "l_ukca_chem_plev", default=False, type_="logical")
        if l_ukca_chem_plev:
            h_vers[atmos_im - 1][51] = 1

    # A52 UKCA ASAD on pressure levels - on if l_ukca_asad_plev is true
    if l_ukca:
        l_ukca_asad_plev = _get_var(config, "namelist:run_ukca",
                  "l_ukca_asad_plev", default=False, type_="logical")

        if l_ukca_asad_plev:
            h_vers[atmos_im - 1][52] = 1

    # A53 Idealised diagnostics
    l_idealised_data = _get_var(config, "namelist:run_dyntest",
                         "l_idealised_data", default=False, type_="logical")
    if l_idealised_data:
        h_vers[atmos_im - 1][53] = 1

    return h_vers


def convert_type(value, type_):
    """Cast based on Fortran types."""
    if isinstance(value, list):
        for i, val in enumerate(value):
            value[i] = convert_type(val, type_)
        return value
    if type_ == "integer":
        return int(value)
    if type_ in ["real", "double precision"]:
        return float(value)
    if type_ in ["logical"]:
        return (value.lower() == ".true.")
    if type_ == "character":
        return value.strip("'")


def _get_tracer_a(config, a_max_trvars):
    # Replicate tracer_a setup in free_tracers_inputs_mod.f90
    tracer_a = []
    l_free_tracer = _get_var(config, "namelist:run_free_tracers",
                            "l_free_tracer", default=False, type_="logical")
    if not l_free_tracer:
        for i in range(a_max_trvars):
            tracer_a.append(False)
    else:
        tca = _get_var(config, "namelist:run_free_tracers", "i_free_tracer",
                       type_="integer", array=True)
        for i in range(a_max_trvars):
            if tca[i] == 0:
                tracer_a.append(False)
            else:
                tracer_a.append(True)
    return tracer_a


def _get_var(config, section, option, default=None, array=False,
             type_=None):
    # Get a namelist option from the config.
    # If an array, call with array=True.
    # Use type_ to cast it to the appropriate type - e.g. "integer".
    node = config.get([section, option], no_ignore=True)
    if node is None:
        if default is None:
            raise ConfigItemNotFoundError(section, option)
            return
        return default
    if array:
        return convert_type(rose.variable.array_split(node.value), type_)
    return convert_type(node.value, type_)


def _form_msg(option_code, value, text):
    """Return a formatted text
    """

    msg_text = "Option code {0} = {1} : {2}"
    return msg_text.format(option_code, value, text)

def _check_chem(config, noption):
    """
    Check option code for chemistry scheme
    The same logic is used whatever aerosol scheme
    version is on, but we call this function with 
    a different option code depending on the value 
    of i_mode_setup
    """

    # If n is zero, this is always off
    if noption == 0:
      l_mask = False

    # If n is one, this is always on 
    elif noption == 1:
      l_mask = True

    # If n is 2 then it is on if aerosol chemistry on
    elif noption == 2:
      l_mask = _get_var(config, "namelist:run_ukca", "l_ukca_chem_aero",
               default=False, type_="logical")

    # If n is 3 then it is on if new emission system (NetCDF) on
    elif noption == 3:
      l_mask = _get_var(config, "namelist:run_ukca", "l_ukca_new_emiss",
               default=False, type_="logical")

    # this is an error - raise an exception
    else:
      l_mask = False
      raise OptionNotFoundError("_check_chem option code {0} not found:"
        .format(noption))

    return l_mask


def _check_glomap(config, noption):

    """
    Check option code for GLOMAP aerosol scheme
    The same logic is used whatever aerosol scheme
    version is on, but we call this function with
    a different option code depending on the value
    of i_mode_setup
    """

    # If n is zero, this is always off
    if noption == 0:
        l_mask = False

    # If n is one, this is always on
    elif noption == 1:
        l_mask = True

    # If n is 2 then it is on if the tropospheric heterogenous
    # chemistry is on
    elif noption == 2:
        l_mask = _get_var(config, "namelist:run_ukca", "l_ukca_trophet",
                          default=False, type_="logical")

    # If n is 3 then it is on if ACTIVATE is on
    elif noption == 3:
        l_mask = _get_var(config, "namelist:run_ukca", "l_ukca_arg_act",
                          default=False, type_="logical")

    # If n is 4 then it is on if aie1 or aie2 is on or
    # ACTIVATE is on
    elif noption == 4:
        l_ukca_arg_act = _get_var(config, "namelist:run_ukca",
                                  "l_ukca_arg_act",
                                  default=False, type_="logical")
        l_ukca_aie1 = _get_var(config, "namelist:run_ukca", "l_ukca_aie1",
                               default=False, type_="logical")
        l_ukca_aie2 = _get_var(config, "namelist:run_ukca", "l_ukca_aie2",
                               default=False, type_="logical")
        l_mask = l_ukca_aie1 or l_ukca_aie2 or l_ukca_arg_act

    # If n is 5 then it is on if RADAER is on
    elif noption == 5:
        l_mask = _get_var(config, "namelist:run_ukca", "l_ukca_radaer",
                          default=False, type_="logical")
    # this is an error - raise an exception
    else:
        l_mask = False
        raise OptionNotFoundError("_check_glomap option code {0} not found:"
                                  .format(noption))

    return l_mask


def _tstmsk_ukca(config,   n1,  n2,  n3,  n4,  n5,  n6,  n7,  n8,  n9,
                 n10, n11, n12, n13, n14, n15, n16, n17, n18, n19, n20,
                 n21, n22, n23, n24, n25, n26, n27, n28, n29, n30, l_ukca,
                 l_ukca_mode, sum_iopn):

    """
    UKCA prognostics and diagnostics: sections 34,50,51,52
    This code has to replicate logic of tstmsk_ukca in the Fortran code
    Option codes for the same item number in paired sections
    34-51, 50-52 must be the same.

    Function returns a tuple with
    l_mask: Logical. Is this item available?
    msg:    If item is not available, this is set to a message to the user
            to explain why not.
    """

    # Set message to empty string by default
    # If the item is not available, this needs to be set
    # to a message which helps the user understand why it is not
    # available
    msg = ''
    if not l_ukca:
        # UKCA is off
        l_mask = False
        msg = "UKCA is off"
        rc_tu = (l_mask, msg)
        return rc_tu

    if sum_iopn == 0:
        # always available for all zeroes
        l_mask = True

    # If n30 is zero, then the chemistry scheme in use controls
    # availability
    elif n30 == 0:

        # Logical for Age-of-air - independent of chem scheme but
        # currently not set for RAQ
        l_ukca_ageair = _get_var(config, "namelist:run_ukca",
                                 "l_ukca_ageair", default=False,
                                 type_="logical")

        i_ukca_chem = _get_var(config, "namelist:run_ukca",
                               "i_ukca_chem", type_="integer")

        # For each chemistry scheme, set a string representation
        # of the option code and a name to use in reporting if
        # an item is not available
        nstr = ''
        if i_ukca_chem == 0 and l_ukca_ageair:
            nstr = 'n1'
            chem_name = 'Age-of-air only'

        if i_ukca_chem == 11:
            nstr = 'n2'
            chem_name = "Standard Tropospheric"

        elif i_ukca_chem == 13:
            nstr = 'n3'
            chem_name = "Regional air quality"

        elif i_ukca_chem == 14:
            nstr = 'n4'
            chem_name = "Offline oxidants BE"

        elif i_ukca_chem == 50:
            nstr = 'n50'
            chem_name = "Tropospheric plus isoprene"

        elif i_ukca_chem == 51:
            nstr = 'n5'
            chem_name = "Stratospheric plus tropospheric chemistry"

        elif i_ukca_chem == 52:
            nstr = 'n6'
            chem_name = "Standard stratospheric chemistry"

        elif i_ukca_chem == 54:
            nstr = 'n7'
            chem_name = "Offline oxidants N-R"

        # if the scheme is not one of the above, and the age of
        # air code is not on, then this is an error
        elif (not l_ukca_ageair):
            l_mask = False
            msg = "Sec 34, 51: unknown chemistry scheme code"

        # Having captured names and option codes,
        # use _check_chem to find if this is on or not
        try:
            # we use eval(nstr) to get the value of the option
            # code set above e.g. if nstr='n1' and n1 is set to 3
            # then eval(nstr) will return 3
            l_mask = _check_chem(config, eval(nstr))
            if not (l_mask):
                msg = _form_msg(nstr, eval(nstr), chem_name)
        # If the option code is not known, _check_glomap raises
        # an exception.
        except:
            l_mask = False
            msg = "_check_chem raised exception: unknown option code: {0}" \
                  .format(eval(nstr))

        # Check n1 for UKCA Age-of-air. Done separately here to avoid
        # possibility of re-setting by other schemes
        if (not l_mask and l_ukca_ageair):
            if n1 == 1:
                l_mask = True
            else:
                l_mask = False
                msg = _form_msg("n1", n1, "Age of air")

    # If n30 is one then controlled by the variable i_mode_setup
    # i.e. which aerosol scheme is in use
    elif n30 == 1:
        if not l_ukca_mode:
            # GLOMAP mode is off
            l_mask = False
            msg = "GLOMAP mode is off"
            rc_tu = (l_mask, msg)
            return rc_tu

        else:

            # find the value of i_mode_setup
            i_mode_setup = _get_var(config, "namelist:run_ukca",
                                    "i_mode_setup", type_="integer")

            # use the _check_glomap function
            # to check if it is on


            # grab the relevant option code, n1 for i_mode_setup == 1
            # etc
            if i_mode_setup == 1:
                nstr = 'n1'
                n = n1
            elif i_mode_setup == 2:
                nstr = 'n2'
                n = n2
            elif i_mode_setup == 6:
                nstr = 'n6'
                n = n6
            elif i_mode_setup == 8:
                nstr = 'n8'
                n = n8
                
            # currently only support values of i_mode_setup 1,2,6 and 8
            else:
                l_mask = False
                msg = "Sec 34, 50, 51, 52: unknown i_mode_setup code"
                rc_tu = (l_mask, msg)
                return rc_tu

            # Use _check_glomap to find if this is on or not
            try:
                l_mask = _check_glomap(config, n)
                if not (l_mask):
                    msg = _form_msg(nstr, n, "i_mode_setup is " +
                                    str(i_mode_setup))

            # If the option code is not known, _check_glomap raises
            # an exception.
            except:
                l_mask = False
                msg = "_check_glomap raised exception: " + \
                        "unknown option code: {0}".format(n)


    rc_tu = (l_mask, msg)
    return rc_tu
