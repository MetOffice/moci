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


class drivers02_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""
    BEFORE_TAG = "drivers_0.2"
    AFTER_TAG = "drivers02_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Driver make app configuration."""
        # Input your macro commands here
        return config, self.reports
