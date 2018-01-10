import rose.upgrade
import sys

class UpgradeError(Exception):

    """Exception created when an upgrade fails."""

    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        sys.tracebacklimit = 0
        return self.msg

    __str__ = __repr__


class OPTv2v3(rose.upgrade.MacroUpgrade):

    """Upgrade macro for MOCI ticket #286 by julienpalmieri."""

    BEFORE_TAG = "OPT-v2"
    AFTER_TAG = "OPT-v3"

    def upgrade(self, config, meta_config=None):
        """Upgrade an Ocean Passive Tracers make app configuration."""
        # Input your macro commands here
        return config, self.reports



