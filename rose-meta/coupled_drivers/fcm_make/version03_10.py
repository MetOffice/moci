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


class drivers10(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #203 by Harry Shepherd."""
    BEFORE_TAG = "drivers_0.3"
    AFTER_TAG = "drivers_1.0"

    def upgrade(self, config, meta_config=None):
        '''Upgrade the tags'''
        self.change_setting_value(config, ["env", "config_rev"],
                                  "@drivers_1.0")
        self.change_setting_value(config, ["env", "driver_rev"],
                                  "drivers_1.0")
        return config, self.reports
