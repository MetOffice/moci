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


class pp11_t76(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #76 by EricaNeininger."""
    BEFORE_TAG = "pp11_t75"
    AFTER_TAG = "pp11_t76"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:nemopostproc",
                          "archive_iceberg_trajectory",], 'false')
        return config, self.reports


class pp11_t37(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #37 by EricaNeininger."""
    BEFORE_TAG = "pp11_t76"
    AFTER_TAG = "pp11_t37"

    def upgrade(self, config, meta_config=None):
        """
        New options to allow individual fieldsfiles to be converted
        to pp format at the user's discretion.
        """
        self.add_setting(config, ["namelist:archiving",
                                  "convert_all_streams",], "true")
        self.add_setting(config, ["namelist:archiving",
                                  "archive_as_fieldsfiles",], None)
        
        return config, self.reports


class pp11_t80(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #80 by harryshepherd."""
    BEFORE_TAG = "pp11_t37"
    AFTER_TAG = "pp11_t80"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        # Input your macro commands here
        self.add_setting(config,
                         ["file:monitorpp.nl", "source"],
                         "namelist:monitoring")
        self.add_setting(config,
                         ["namelist:monitoring", "ltimer"],
                         "false")
        
        return config, self.reports


