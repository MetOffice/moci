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


class pp23_t550(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #550, committed under #548 by EricaNeininger."""
    BEFORE_TAG = "postproc_2.3"
    AFTER_TAG = "pp23_t548"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        self.add_setting(config,
                         ["namelist:archiving", "archive_ncf",], "true")
        return config, self.reports


class pp23_t495(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #495 by EricaNeininger."""
    BEFORE_TAG = "pp23_t548"
    AFTER_TAG = "pp23_t495"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        self.add_setting(config,
                         ["namelist:atmospp", "preserve_ozone",],
                         "false")
        self.add_setting(config,
                         ["namelist:atmospp", "ozone_source_stream",],
                         "p")
        self.add_setting(config,
                         ["namelist:atmospp", "ozone_output_stream",],
                         "")
        self.add_setting(config,
                         ["namelist:atmospp", "ozone_fields",],
                         "00253,30453")
        return config, self.reports


class pp23_t577(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #577 by Erica Neininger."""
    BEFORE_TAG = "pp23_t495"
    AFTER_TAG = "postproc_2.4"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration to postproc_2.4."""
        
        return config, self.reports
