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


class pp24_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXX by <Author>."""
    BEFORE_TAG = "postproc_2.4"
    AFTER_TAG = "postproc_2.5"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration to postproc_2.5."""
        
        return config, self.reports
