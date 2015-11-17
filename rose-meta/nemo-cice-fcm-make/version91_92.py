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



class vn91_t6298(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #6298 by Paul Cresswell."""

    BEFORE_TAG = "vn9.1"
    AFTER_TAG = "vn9.1_t6298"

    def upgrade(self, config, meta_config=None):
        # Get default revisions from the correct ocean version file:
        ocean_version = self.get_setting_value(config,
                        ["env", "ocean_version_file"])
        if not ocean_version:
            # Should exist, but here's the default anyway:
            ocean_version = 'nemo3.2-cice4.1-version.cfg'

        if ocean_version == 'nemo3.2-cice4.1-version.cfg':
            nemo_rev = 'vn3.2'
            ioipsl_rev = 'vn3.0'
            cice_rev = 'vn4.1'
        else:
            nemo_rev = 'vn3.4'
            ioipsl_rev = 'vn3.4'
            cice_rev = 'vn4.1m1'

        # These are now compulsory=true; values match central configs:
        self.add_setting(config, ["env", "nemo_rev"],   nemo_rev)
        self.add_setting(config, ["env", "ioipsl_rev"], ioipsl_rev)
        self.add_setting(config, ["env", "cice_rev"],   cice_rev)

        # Also now compulsory=true; should make it easier to apply overrides:
        self.add_setting(config, ["env", "fcflags_cice_overrides"], "")
        self.add_setting(config, ["env", "fcflags_nemo_overrides"], "")
        self.add_setting(config, ["env", "ldflags_overrides_prefix"], "")
        self.add_setting(config, ["env", "ldflags_overrides_suffix"], "")

        # Merge preprocess-ocean and build-ocean buttons into one.
        preprocess = self.get_setting_value(config, ["env","preprocess_ocean"])
        build = self.get_setting_value(config, ["env", "build_ocean"])
        # But do we *actually* do these things?
        do_preprocess = self.get_setting_value(config, 
                        ["env", "preprocess_ocean"], no_ignore=True)
        do_build = self.get_setting_value(config,
                   ["env", "build_ocean"], no_ignore=True)

        partial_compiles = []
        # Save any setups that can't be captured by the new button:
        if do_preprocess and not do_build:
            partial_compiles.append(preprocess)
        elif do_build and not do_preprocess:
            partial_compiles.append(build)

        if preprocess and build:
            value = 'preprocess-ocean build-ocean'
        else:
            value = ''
        self.add_setting(config, ["env", "compile_ocean"], value)

        self.remove_setting(config, ["env", "preprocess_ocean"])
        self.remove_setting(config, ["env", "build_ocean"])

        # That covers most cases. Apps where the ocean exec is built OR
        # preprocessed (but not both) need their steplists overridden manually.

        # Decide how to split this up between the local and remote steplists
        # using the same logic as vn90_t6288.
        # This is only needed if there are *compile* steps to process manually
        # (extract and mirror settings are unaffected).

        if partial_compiles:

            remote_steps = ' '.join(partial_compiles)

            platform = self.get_setting_value(config,
                       ["env", "platform_config_dir"])
            steplist = ''
            mirror_steplist = ''
            if (platform == 'meto-pwr7-xlf'
             or platform == 'nci-x86-ifort'
             or platform == 'ncas-xc30-cce'):
                # Two-stage build required.
                # Local steplist is handled via the extract/mirror buttons.
                mirror_steplist = remote_steps

            elif (platform == 'meto-x86-ifort'
               or platform == 'kma-xe6-cce'):
                # One-stage build required.
                # We have to merge local and remote steplists.

                # See if we need to extract and mirror:
                extract = self.get_setting_value(config, ["env", "extract"],
                                                 no_ignore=True)
                mirror = self.get_setting_value(config, ["env", "mirror"],
                                                no_ignore=True)
                local_steplist = []
                if extract:
                    local_steplist.append(extract)
                if mirror:
                    local_steplist.append(mirror)

                local_steps = ' '.join(local_steplist)
                steplist = local_steps + ' ' + remote_steps

            else:
               # Don't know - we may have disabled a remote compile sub-step.
               # Leave a message to warn the user.
                warn_msg = """
     !!!!! Your compilation (make step) settings may have changed. !!!!!
     !!!!! Please use the steplist or mirror_steplist variables to !!!!!
     !!!!! restore a missing preprocess or build step.             !!!!!
                           """
                self.add_report(info=warn_msg, is_warning=True)

            if steplist:
                self.add_setting(config, ["env", "steplist"], steplist)
            if mirror_steplist:
                self.add_setting(config, ["env", "mirror_steplist"],
                                 mirror_steplist)

        return config, self.reports


class vn92_t6571(rose.upgrade.MacroUpgrade):

    BEFORE_TAG = "vn9.1_t6298"
    AFTER_TAG = "vn9.2"

    def upgrade(self, config, meta_config=None):
        """Upgrade configuration to next major version."""

        config_revision = self.get_setting_value(config, ['env', 'config_revision'])
        config_root = self.get_setting_value(config, ['env', 'config_root_path'])
        if config_root == '$SOURCE_UM_BASE':
            pass
        else:
            config_root = 'fcm:um_tr'
            config_revision = '@vn9.2'
            self.add_report('env', 'config_root_path', config_root, 
                info='Upgrading fcm_make config version to trunk@vn9.2',
                is_warning=True)
        self.change_setting_value(config, ['env', 'config_revision'], config_revision)
        self.change_setting_value(config, ['env', 'config_root_path'], config_root)

        return config, self.reports

