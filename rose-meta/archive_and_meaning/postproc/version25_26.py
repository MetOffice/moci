import re
import sys
if sys.version_info[0] == 2:
    from rose.upgrade import MacroUpgrade
else:
    from metomi.rose.upgrade import MacroUpgrade

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__


class pp25_t678(MacroUpgrade):

    """Upgrade macro for ticket #678 by pierresiddall."""
    BEFORE_TAG = "postproc_2.5"
    AFTER_TAG = "pp25_t678"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration to add missing metadata."""
        try:
            cice_age = self.get_setting_value(config, ["namelist:ciceverify", "cice_age"])
            self.remove_setting(config, ["namelist:ciceverify", "cice_age"])
        except AttributeError:
            cice_age = "false"
        
        self.add_setting(config,["namelist:ciceverify","cice_age_rst"], cice_age)
        base = self.get_setting_value(config, ["namelist:nemo_processing", "base_component"])
        self.add_setting(config,["namelist:nemoverify","base_mean"], base)

        icebergs = self.get_setting_value(config, ["namelist:nemoverify", "nemo_icebergs_rst"])
        nemo_vn = "pre-4.2" if icebergs == "true" else "4.2+"       
        self.add_setting(config,["namelist:nemoverify","nemo_version"], nemo_vn)
        self.add_setting(config,["namelist:nemoverify","nemo_ice_rst"], "false")
        self.add_setting(config,["namelist:nemoverify","nemo_icb_rst"], "false")
        
        return config, self.reports

class pp25_t646(MacroUpgrade):

    """Upgrade macro for ticket #646 by Marc Stringer."""
    BEFORE_TAG = "pp25_t678"
    AFTER_TAG = "pp25_t646"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration include UniCiCles."""
        self.add_setting(config, ["command", "pp_unicicles"],
                         "run_python_env.sh main_pp.py unicicles")
        self.add_setting(config,
                         ["file:uniciclespp.nl", "source"],
                         ("namelist:unicicles_pp namelist:suitegen " +
                          "(namelist:moose_arch) (namelist:archer_arch) " +
                          "(namelist:script_arch)"))
        verify_source = self.get_setting_value(config,
                                               ["file:verify.nl", "source"])
        verify_source += " (namelist:uniciclesverify)"
        self.change_setting_value(config,
                                  ["file:verify.nl", "source"], verify_source)

        ## PostProc App
        self.add_setting(config, ["namelist:unicicles_pp",
                                  "pp_run"], "false")
        self.add_setting(config, ["namelist:unicicles_pp",
                                  "share_directory"], "$UNICICLES_DATA")
        self.add_setting(config, ["namelist:unicicles_pp",
                                  "cycle_length"], "1y")

        # archive_integrity App
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "verify_model"], "false")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "meanfields"],
                         "atmos-icecouple,bisicles-icecouple,calving")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "meanstreams"], "1y")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "cycle_length"], "1y")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "unicicles_bisicles_ais_rst"], "false")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "unicicles_bisicles_gris_rst"], "false")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "unicicles_glint_ais_rst"], "false")
        self.add_setting(config, ["namelist:uniciclesverify",
                                  "unicicles_glint_gris_rst"], "false")

        return config, self.reports
