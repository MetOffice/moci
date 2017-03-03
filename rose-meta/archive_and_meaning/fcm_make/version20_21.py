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


class pp20_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""
    BEFORE_TAG = "postproc_2.0"
    AFTER_TAG = "pp20_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Input your macro commands here
        return config, self.reports

class pp20_t109(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #109 by Erica Neininger."""
    BEFORE_TAG = "postproc_2.0"
    AFTER_TAG = "pp20_t109"

    def upgrade(self, config, meta_config=None):
        """Adding source for new verification app"""

        # Additional source for new verification app
        self.add_setting(config,
                         ["env", "verify_config",],
                         "verify.cfg")

        return config, self.reports
