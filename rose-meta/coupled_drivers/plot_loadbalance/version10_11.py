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


class drivers10_t306(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #306 by Harry Shepherd."""
    BEFORE_TAG = "drivers_1.0"
    AFTER_TAG = "drivers_1.1"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Driver make app configuration."""
        # Input your macro commands here
        return config, self.reports
