import rose.upgrade
import re
import sys

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__


class pp12_pp20(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""
    BEFORE_TAG = "postproc_1.2"
    AFTER_TAG = "postproc_2.0"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Upgrade extract revision keywords
        self.change_setting_value(config, ["env", "config_base"],
                                  "fcm:moci.xm_tr", forced=True)
        self.change_setting_value(config, ["env", "config_rev"],
                                  "@postproc_2.0", forced=True)
        self.change_setting_value(config, ["env", "pp_rev"],
                                  "postproc_2.0", forced=True)

        return config, self.reports
