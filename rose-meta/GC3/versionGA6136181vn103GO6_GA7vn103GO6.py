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


class ga7beta_t1282(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #1282 by Nic Gedney."""

    BEFORE_TAG = "GA6.136.18.1-vn10.3_GO6"
    AFTER_TAG = "GA7-vn10.3_GO6"

    def upgrade(self, config, meta_config=None):
        """Upgrade a UM runtime app configuration."""
        # Input your macro commands here

        self.add_setting(config, ["namelist:jules_hydrology", "nfita"], "20")
        return config, self.reports
