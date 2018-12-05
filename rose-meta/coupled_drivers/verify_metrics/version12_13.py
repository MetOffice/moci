import sys
import rose.upgrade

class UpgradeError(Exception):

    """Exception created when an upgrade fails."""

    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        sys.tracebacklimit = 0
        return self.msg

    __str__ = __repr__


class drivers12_t369(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #369 by Harry Shepherd."""
    BEFORE_TAG = "drivers_1.2"
    AFTER_TAG = "drivers_1.3"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Driver make app configuration."""
        # Input your macro commands here
        return config, self.reports
