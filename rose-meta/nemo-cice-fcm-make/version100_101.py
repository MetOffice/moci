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



class vn100_tXXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""

    BEFORE_TAG = "vn10.0"
    AFTER_TAG = "vn10.0_tXXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a NEMO-CICE fcm-make app configuration."""
        # Input your macro commands here
        return config, self.reports


class vn101_t327(rose.upgrade.MacroUpgrade):

    BEFORE_TAG = "vn10.0_tXXXX"
    AFTER_TAG = "vn10.1"

    def upgrade(self, config, meta_config=None):
        """Upgrade configuration to next major version."""

        config_revision = self.get_setting_value(config, ['env', 'config_revision'])
        config_root = self.get_setting_value(config, ['env', 'config_root_path'])
        if config_root == '$SOURCE_UM_BASE':
            pass
        else:
            config_root = 'fcm:um.xm_tr'
            config_revision = '@vn10.1'
            self.add_report('env', 'config_root_path', config_root, 
                info='Upgrading fcm_make config version to trunk@vn10.1',
                is_warning=True)
        self.change_setting_value(config, ['env', 'config_revision'], config_revision)
        self.change_setting_value(config, ['env', 'config_root_path'], config_root)

        return config, self.reports

