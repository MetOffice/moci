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


class pp20_t100(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #100 by Pierre Mathiot."""
    BEFORE_TAG = "postproc_2.0"
    AFTER_TAG = "pp20_t100"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                        ["namelist:nemopostproc", "msk_rebuild",], "false")
        return config, self.reports


class pp20_t189(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #189 by Erica Neininger."""
    BEFORE_TAG = "pp20_t100"
    AFTER_TAG = "pp20_t189"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Input your macro commands here
        self.add_setting(config, ["namelist:moose_arch", "non_duplexed_set"],
                         "false")
        return config, self.reports


class pp12_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""
    BEFORE_TAG = "pp20_tXXX"
    AFTER_TAG = "pp20_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Input your macro commands here
        return config, self.reports
