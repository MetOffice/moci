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


class pp22_t282(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #282 by Erica Neininger."""
    BEFORE_TAG = "postproc_2.2"
    AFTER_TAG = "pp22_t282"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:nemo_processing", "create_decadal_mean",],
                         "false")
        self.add_setting(config,
                         ["namelist:cice_processing", "create_decadal_mean",],
                         "false")

        return config, self.reports


class pp22_t289(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #289 by DaveStorkey."""
    BEFORE_TAG = "pp22_t282"
    AFTER_TAG = "pp22_t289"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:nemoverify", "nemo_ice_rst",],
                         "false")

        return config, self.reports


class pp22_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXX by <Author>."""
    BEFORE_TAG = "pp22_t289"
    AFTER_TAG = "pp22_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        # Add changes here...

        return config, self.reports
