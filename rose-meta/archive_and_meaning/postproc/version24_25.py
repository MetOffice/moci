import re
import sys
if sys.version_info[0] == 2:
    from rose.upgrade import MacroUpgrade
else:
    from metomi.rose.upgrade import MacroUpgrade

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__


class pp24_t588(MacroUpgrade):

    """Upgrade macro for ticket #588 by Rosalyn Hatcher."""
    BEFORE_TAG = "postproc_2.4"
    AFTER_TAG = "pp24_t588"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        self.add_setting(config,
                         ["command", "jdma"], "jdma.py")
        self.add_setting(config,
                         ["file:jasmin.nl", "source"], "namelist:suitegen (namelist:pptransfer) (namelist:archer_arch) (namelist:jasmin_arch)")
        self.add_setting(config,
                         ["namelist:pptransfer", "globus_cli"], "true")
        self.add_setting(config,
                         ["namelist:pptransfer", "globus_notify"], "'off'")
        self.add_setting(config,
                         ["namelist:pptransfer", "globus_default_colls"], "true")
        self.add_setting(config,
                         ["namelist:pptransfer", "globus_src_coll"], "")
        self.add_setting(config,
                         ["namelist:pptransfer", "globus_dest_coll"], "")
        self.add_setting(config,
                         ["namelist:jasmin_arch", "default_workspace"], "true")
        self.add_setting(config,
                         ["namelist:jasmin_arch", "workspace"], "")
        self.add_setting(config,
                         ["namelist:jasmin_arch", "jasmin_copy"], "false")
        self.add_setting(config,
                         ["namelist:jasmin_arch", "copy_streams"], "")
        self.add_setting(config,
                         ["namelist:jasmin_arch", "copy_target"], "")

        self.remove_setting(config, ["namelist:pptransfer", "gridftp"])

        return config, self.reports


class pp24_t674(MacroUpgrade):

    """Upgrade macro for ticket #674 by Erica Neininger."""
    BEFORE_TAG = "pp24_t588"
    AFTER_TAG = "postproc_2.5"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration to postproc_2.5."""

        return config, self.reports

