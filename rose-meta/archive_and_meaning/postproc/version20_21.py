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


class pp20_t100(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #100 by Pierre Mathiot."""
    BEFORE_TAG = "postproc_2.0"
    AFTER_TAG = "pp20_t100"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                        ["namelist:nemopostproc", "msk_rebuild",], "false")
        return config, self.reports


class pp20_t189(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #189 by Erica Neininger."""
    BEFORE_TAG = "pp20_t100"
    AFTER_TAG = "pp20_t189"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Input your macro commands here
        self.add_setting(config, ["namelist:moose_arch", "non_duplexed_set"],
                         "false")
        return config, self.reports


class pp20_t109(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #109 by Erica Neininger."""
    BEFORE_TAG = "pp20_t189"
    AFTER_TAG = "pp20_t109"

    def upgrade(self, config, meta_config=None):
        """Adding new verification app."""

        # Additional namelists for new verification app
        self.add_setting(config,
                         ["command", "verify",],
                         "archive_integrity.py")

        self.add_setting(config, ["file:verify.nl", "source",],
                         "namelist:commonverify (namelist:atmosverify) "
                         "(namelist:ciceverify) (namelist:nemoverify)")

        atmos_dump = self.get_setting_value(config, ["namelist:archiving",
                                                     "arch_dump_freq"])
        self.add_setting(config,
                         ["namelist:atmosverify", "archive_timestamps",],
                         atmos_dump)
        self.add_setting(config,
                         ["namelist:atmosverify", "mean_reference_date",],
                         "20001201")
        self.add_setting(config,
                         ["namelist:atmosverify", "streams_30d",], None)
        self.add_setting(config,
                         ["namelist:atmosverify", "streams_90d",], None)
        ffarch = self.get_setting_value(config, ["namelist:archiving",
                                                 "process_all_streams"])
        if ffarch.lower() != "true":
              ffstreams = self.get_setting_value(config,
                                                 ["namelist:archiving",
                                                  "archive_as_fieldsfiles"])
              self.add_setting(config, ["namelist:atmosverify", "ff_streams"],
                               ffstreams)
        self.add_setting(config,
                         ["namelist:atmosverify", "timelimitedstreams",],
                         "false")
        self.add_setting(config,
                         ["namelist:atmosverify", "tlim_streams",], None)
        self.add_setting(config,
                         ["namelist:atmosverify", "tlim_starts",], None)
        self.add_setting(config,
                         ["namelist:atmosverify", "tlim_ends",], None)

        self.add_setting(config,
                         ["namelist:commonverify", "dataset",],
                         "moose:crum/$CYLC_SUITE_NAME")
        self.add_setting(config,
                         ["namelist:commonverify", "prefix",], "$RUNID")
        self.add_setting(config,
                         ["namelist:commonverify", "startdate",], "$DATE1")
        self.add_setting(config,
                         ["namelist:commonverify", "enddate",], "$DATE2")
        self.add_setting(config, ["namelist:commonverify",
                                  "check_additional_files_archived",], "true")

        self.add_setting(config,
                         ["namelist:ciceverify", "cice_age",], "false")
        self.add_setting(config,
                         ["namelist:ciceverify", "archive_timestamps",],
                         "Biannual")
        buff_crst = self.get_setting_value(config, ["namelist:cicepostproc",
                                                    "buffer_archive"])
        self.add_setting(config,
                         ["namelist:ciceverify", "buffer_restart",], buff_crst)
        self.add_setting(config,
                         ["namelist:ciceverify", "restart_suffix",], ".nc")
        arch_means = self.get_setting_value(config, ["namelist:cicepostproc",
                                                     "means_to_archive"])
        self.add_setting(config,
                         ["namelist:ciceverify", "meanstreams",],
                         ','.join(["1m,1s,1y", arch_means]))


        iberg = self.get_setting_value(config, ["namelist:nemopostproc",
                                                "archive_iceberg_trajectory"])
        self.add_setting(config,
                         ["namelist:nemoverify", "nemo_icebergs_rst",], iberg)
        self.add_setting(config,
                         ["namelist:nemoverify", "iberg_traj",], iberg)
        self.add_setting(config,
                         ["namelist:nemoverify", "nemo_ptracer_rst",], "false")
        self.add_setting(config,
                         ["namelist:nemoverify", "archive_timestamps",],
                         "Biannual")
        buff_nrst = self.get_setting_value(config, ["namelist:nemopostproc",
                                                    "buffer_rebuild_rst"])
        self.add_setting(config,
                         ["namelist:nemoverify", "buffer_restart",], buff_nrst)
        buff_mean = self.get_setting_value(config, ["namelist:nemopostproc",
                                                    "buffer_rebuild_mean"])
        self.add_setting(config,
                         ["namelist:nemoverify", "buffer_mean",], buff_mean)
        arch_means = self.get_setting_value(config, ["namelist:nemopostproc",
                                                     "means_to_archive"])
        self.add_setting(config,
                         ["namelist:nemoverify", "meanstreams",],
                         ','.join(["1m,1s,1y", arch_means]))
        self.add_setting(config, ["namelist:nemoverify", "fields",],
                         "grid-T,grid-U,grid-V,grid-W")

        # Pattern added for nemo/cice archive_timestamps - commonly used syntax
        # "YY-DD" will not match the pattern - update by removing quotes to
        # avoid errors
        for naml in ['nemopostproc', 'cicepostproc']:
              tstamp = self.get_setting_value(config, ["namelist:" + naml,
                                                       "archive_timestamps"])
              tstamp = tstamp.replace('"', "").replace("'", "")
              self.change_setting_value(config, ["namelist:" + naml,
                                                 "archive_timestamps"], tstamp)
        rbld_stamp = self.get_setting_value(config, ["namelist:nemopostproc",
                                            "rebuild_timestamps"])
        rbld_stamp = rbld_stamp.replace('"', "").replace("'", "")
        self.change_setting_value(config, ["namelist:nemopostproc",
                                           "rebuild_timestamps"], rbld_stamp)
        
        return config, self.reports


class pp20_tXXX(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #XXXX by <author>."""
    BEFORE_TAG = "pp20_tXXX"
    AFTER_TAG = "pp20_tXXX"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc make app configuration."""
        # Input your macro commands here
        return config, self.reports
