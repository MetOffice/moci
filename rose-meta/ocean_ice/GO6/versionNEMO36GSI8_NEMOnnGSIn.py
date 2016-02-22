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


class go6_cice_nprocs(rose.upgrade.MacroUpgrade):

    """Upgrade macro for setting default value of cice nprocs"""

    BEFORE_TAG = "nemo36_gsi8"
    AFTER_TAG = "HEAD"

    def upgrade(self, config, meta_config=None):
        """Upgrade a GO6 runtime app configuration."""
        # Input your macro commands here

        self.change_setting_value(config, ["namelist:domain_nml", "nprocs"],
                                  "'set_by_system'")
        return config, self.reports
