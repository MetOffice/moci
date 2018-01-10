import rose.upgrade
import sys

class UpgradeError(Exception):

    """Exception created when an upgrade fails."""

    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        sys.tracebacklimit = 0
        return self.msg

    __str__ = __repr__


class OPTv1v2(rose.upgrade.MacroUpgrade):

    """Upgrade macro for MOCI ticket #205 by julienpalmieri."""

    BEFORE_TAG = "OPT-v1"
    AFTER_TAG = "OPT-v2"

    def upgrade(self, config, meta_config=None):
        """Upgrade an Ocean Passive Tracers make app configuration."""
        # Input your macro commands here
        self.remove_setting(config, ["namelist:namcfcdia"],
              info="remove obsolete CFCs namelist namcfcdia -- GMED #340.")
        self.remove_setting(config, ["namelist:nammeddia"],
              info="remove obsolete MEDUSA namelist nammeddia -- GMED #340. ")
        self.change_setting_value(config, ["file:namelist_cfc_cfg", "source"], 
              "namelist:namcfcdate",
              info="remove obsolete namcfcdia of file list -- GMED #340. ")
        self.change_setting_value(config, ["file:namelist_medusa_cfg", 
              "source"],
              "namelist:natbio namelist:natroam namelist:natopt " + \
              "namelist:nammedsbc",
              info="remove obsolete nammeddia offile list -- GMED #340. ")
        self.add_setting(config, ["namelist:natbio", "chl_out"], "1",
              info="Add Chl_out for Coupled Chl scaling -- GMED #351.")
        self.add_setting(config, ["namelist:natbio", "scl_chl"], "1.0",
              info="Add scl_chl for Coupled Chl scaling -- GMED #351.")
        self.remove_setting(config, ["namelist:namtrc_trd", 
              "ln_trdmld_trc_instant"],
              info="rename var ln_trdmld_trc_instant --> 1/2 -- GMED #338.")
        self.add_setting(config, ["namelist:namtrc_trd", 
              "ln_trdmxl_trc_instant"], ".true.",
              info="rename var --> ln_trdmxl_trc_instant 2/2 -- GMED #338.")
        self.remove_setting(config, ["namelist:namtrc_trd", 
              "ln_trdmld_trc_restart"],
              info="rename var ln_trdmld_trc_restart --> 1/2 -- GMED #338.")
        self.add_setting(config, ["namelist:namtrc_trd", 
              "ln_trdmxl_trc_restart"], ".false.",
              info="rename var --> ln_trdmxl_trc_restart 2/2 -- GMED #338.")
        self.add_setting(config, ["namelist:natbio","dmscut"], "1.72",
              info="Add DMS tuning param dmscut -- GMED #365.")
        self.add_setting(config, ["namelist:natbio","dmsmin"], "2.29",
              info="Add DMS tuning param dmsmin -- GMED #365.")
        self.add_setting(config, ["namelist:natbio","dmsslp"], "8.24",
              info="Add DMS tuning param dmsslp -- GMED #365.")
        return config, self.reports



