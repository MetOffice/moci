import rose.upgrade
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


class pp10_t48(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #48 by EricaNeininger."""
    BEFORE_TAG = "postproc_1.0"
    AFTER_TAG = "pp10_t48"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""

        self.add_setting(config,
                         ["namelist:suitegen", "nccopy_path",], "")
        self.add_setting(config,
                         ["namelist:nemopostproc", "compress_means",],
                         "'nccopy'")
        self.add_setting(config,
                         ["namelist:cicepostproc", "compress_means",],
                         "'nccopy'")
        self.add_setting(config,
                         ["namelist:nemopostproc", "compression_level",], "0")
        self.add_setting(config,
                         ["namelist:cicepostproc", "compression_level",], "0")
        self.add_setting(config,
                         ["namelist:nemopostproc", "chunking_arguments",],
                         "time_counter/1,y/205,x/289")
        self.add_setting(config,
                         ["namelist:cicepostproc", "chunking_arguments",],
                         "time/1,nc/1,ni/288,nj/204")

        return config, self.reports


class pp10_t28(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #28 by Erica Neininger."""
    BEFORE_TAG = "pp10_t48"
    AFTER_TAG = "pp10_t28"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        # Input your macro commands here
        utils = self.get_setting_value(config,
                                       ["namelist:atmospp", "pumf_path"])
        self.add_setting(config, ["namelist:atmospp", "um_utils"],
                         os.path.dirname(utils))
        self.remove_setting(config, ["namelist:atmospp", "pumf_path"])
        self.add_setting(config, ["namelist:archiving", "convert_pp"], "true")

        return config, self.reports
