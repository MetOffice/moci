import rose.upgrade
import re
import sys
import os

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__


class pp22_t282(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #282 by Erica Neininger."""
    BEFORE_TAG = "postproc_2.2"
    AFTER_TAG = "pp22_t282"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:nemo_processing", "create_decadal_mean",],
                         "false")
        self.add_setting(config,
                         ["namelist:cice_processing", "create_decadal_mean",],
                         "false")

        return config, self.reports


class pp22_t289(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #289 by DaveStorkey."""
    BEFORE_TAG = "pp22_t282"
    AFTER_TAG = "pp22_t289"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:nemoverify", "nemo_ice_rst",],
                         "false")

        return config, self.reports


class pp22_t291(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #291 by Erica Neininger."""
    BEFORE_TAG = "pp22_t289"
    AFTER_TAG = "pp22_t291"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config, ["namelist:atmospp", "create_means"],
                         'false')
        self.add_setting(config, ["namelist:atmospp", "create_monthly_mean"],
                         'false')
        self.add_setting(config, ["namelist:atmospp", "create_seasonal_mean"],
                         'false')
        self.add_setting(config, ["namelist:atmospp", "create_annual_mean"],
                         'false')
        self.add_setting(config, ["namelist:atmospp", "create_decadal_mean"],
                         'false')
        self.add_setting(config, ["namelist:atmospp", "meanbase_stream"],
                         'pm')
        self.add_setting(config, ["namelist:atmospp", "meanbase_period"],
                         '1m')

        for var in ["process_means", "process_streams"]:
            # Split supplied regular expression into list of streamIDs
            expr = self.get_setting_value(config,
                                          ["namelist:atmospp", var])
            if expr:
               spans = '({span})'.format(span='|'.join(
                           re.findall(r'\w-\w', expr)  + [',']))
               split_expr = re.split(spans, expr)
               for elem in list(split_expr):
                    if len(elem) == 0 or elem == ',':
                       split_expr.remove(elem)
                    elif "-" not in elem:
                        elemid = split_expr.index(elem)
                        split_expr[elemid] = elem[0]
                        for i, char in enumerate(elem[1:]):
                            split_expr.insert(elemid + 1 + i, char)
               self.change_setting_value(config,
                                         ["namelist:atmospp", var],
                                         ",".join(split_expr))

            self.add_setting(config,
                             ["namelist:atmosverify", "pp_climatemeans"],
                             'false')

        return config, self.reports

class pp22_t301(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #301 by <Erica Neininger>."""
    BEFORE_TAG = "pp22_t291"
    AFTER_TAG = "pp22_t301"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config, ["namelist:script_arch", "archive_script"], "")
        for arch in ["file:atmospp.nl", "file:nemocicepp.nl"]:
              val = self.get_setting_value(config, [arch, "source"])
              self.change_setting_value(config, [arch, "source"], val + " (namelist:script_arch)")

        return config, self.reports


class pp22_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXX by <Author>."""
    BEFORE_TAG = "pp22_t301"
    AFTER_TAG = "pp22_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        # Add changes here...

        return config, self.reports
