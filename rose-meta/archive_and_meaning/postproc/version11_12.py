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


class pp11_t75(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #75 by EricaNeininger."""
    BEFORE_TAG = "postproc_1.1"
    AFTER_TAG = "pp11_t75"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:cicepostproc", "means_to_archive",], None)
        self.add_setting(config,
                         ["namelist:cicepostproc", "base_component",], '10d')
        self.add_setting(config,
                         ["namelist:nemopostproc", "means_to_archive",], None)
        self.add_setting(config,
                         ["namelist:nemopostproc", "base_component",], '10d')
        return config, self.reports
