import rose.upgrade
import re
import fileinput
import sys

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""
      
      def __init__(self, msg):
          self.msg = msg
      
      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg
          
      __str__ = __repr__


class vn90_t6195(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #6195 by Paul Cresswell.
       Break up the config path into a number of separate options."""

    BEFORE_TAG = "vn9.0"
    AFTER_TAG = "vn9.0_t6195"

    def upgrade(self, config, meta_config=None):
        # Get the current config value:
        inc_config = self.get_setting_value(config, ["env", "include_config"])

        # Break it up into a number of separate options:
        searchObj = re.search(r'^(.*)/fcm-make/(.*)/nemo-cice-(.*)\.cfg(.*)$',
                              inc_config)

        root_path = searchObj.group(1)
        platform_config = searchObj.group(2)
        optimisation = searchObj.group(3)
        config_rev = searchObj.group(4)

        self.add_setting(config, ["env", "config_root_path"], root_path)
        self.add_setting(config, ["env", "platform_config_dir"],
                         platform_config)
        self.add_setting(config, ["env", "optimisation_level"], optimisation)
        self.add_setting(config, ["env", "config_revision"], config_rev)

        # Add to the config file
        filename = './file/fcm-make.cfg'
        new_config = "include = %s/fcm-make/%s/nemo-cice-%s.cfg%s\n" % (
                     '$config_root_path', '$platform_config_dir',
                     '$optimisation_level', '$config_revision')
        for line in fileinput.input([filename], inplace=True):
            if re.match(r'\s*include\s*=', line):
                line = new_config
            sys.stdout.write(line)

        # Remove the old variable
        self.remove_setting(config, ["env", "include_config"])

        return config, self.reports


class vn90_t6274(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #6274 by Paul Cresswell.
       Make both opt. level and OpenMP easily selectable from the GUI."""

    BEFORE_TAG = "vn9.0_t6195"
    AFTER_TAG = "vn9.0_t6274"

    def upgrade(self, config, meta_config=None):
        # Get the current config settings:
        platform    = self.get_setting_value(config, 
                                             ["env", "platform_config_dir"])
        fcflags_omp = self.get_setting_value(config, ["env", "fcflags_omp"])
        ldflags_omp = self.get_setting_value(config, ["env", "ldflags_omp"])

        # Assume OpenMP on to begin
        openmp = 'openmp_on'

        # Check to see if the user has overridden anything.
        warn_user = False
        blank_fcflags = False
        blank_ldflags = False
        if fcflags_omp is not None:
            warn_user = True
            # Use this flag to decide if the user is overriding OpenMP settings.
            if re.search(r'\S', fcflags_omp):
                openmp = 'openmp_on'
            else:
                openmp = 'openmp_off'
                blank_fcflags = True
 
        if ldflags_omp is not None:
            warn_user = True
            if not re.search(r'\S', ldflags_omp):
                blank_ldflags = True

        # If both flags are blank (and so openmp=off) assume we can safely
        # delete both variables. Otherwise leave them as ignored so they're
        # still available to the user if the upgrade settings are wrong.
        if blank_fcflags and blank_ldflags:
            self.remove_setting(config, ["env", "fcflags_omp"])
            self.remove_setting(config, ["env", "ldflags_omp"])
        else:
            self.ignore_setting(config, ["env", "fcflags_omp"])
            self.ignore_setting(config, ["env", "ldflags_omp"])
 
        if warn_user:
            warn_msg = """
     !!!!!    OpenMP compilation and settings have been disabled.      !!!!!
     !!!!! Please check the new openmp setting is correct in your app. !!!!!
                       """
            self.add_report(info=warn_msg, is_warning=True)
 
        self.add_setting(config, ["env", "openmp"], openmp)
 
        return config, self.reports

class vn90_t6288(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #6288 by Paul Cresswell.
       Make steplists easier to control from the GUI."""

    BEFORE_TAG = "vn9.0_t6274"
    AFTER_TAG = "vn9.0_t6288"

    def upgrade(self, config, meta_config=None):

        config_type = self.get_setting_value(config, ["env", "config_type"])
        platform = self.get_setting_value(config,
                                          ["env", "platform_config_dir"])

        # Read and store any steplist settings:
        steplist = self.get_setting_value(config, ["env", "steplist"])
        mirror_steplist = self.get_setting_value(config,
                                                 ["env", "mirror_steplist"])

        steps = ''
        if steplist is not None:
            steps = 'extract mirror'
        else:
            steps = steplist

        if mirror_steplist is not None:
            steps = steps + ' ' + mirror_steplist

        ocean_steps = {'extract'          : 'extract',
                       'mirror'           : 'mirror',
                       'preprocess_ocean' : 'preprocess-ocean',
                       'build_ocean'      : 'build-ocean'}

        """Note that single-stage builds may produce "mirror=", which may need
           changing if the app is later adapted for a different platform.

           One edge case worth attempting to correct: if a 2-stage build app
           (i.e. with an fcm_make2 task) includes $steplist but NOT 
           $mirror_steplist, we will end up with an app which extracts and/or
           mirrors (or neither) but does not build anything! To correct this we
           add the missing steps where we know we can, and warn where we're not
           sure what's required.
        """

        if steplist is not None and mirror_steplist is None:

            # Two-stage build: add the missing steps.
            if (platform == 'meto-pwr7-xlf'
             or platform == 'nci-x86-ifort'
             or platform == 'ncas-xc30-cce'):

                 for key,value in ocean_steps.iteritems():
                     steps = steps + ' ' + value

            # One-stage build: do nothing.
            elif (platform == 'meto-x86-ifort'
               or platform == 'kma-xe6-cce'):
               pass

            # Don't know - we may have disabled the remote build.
            # Leave a message to warn the user.
            else:
                warn_msg = """
     !!!!! If you use an fcm_make2 step your remote make settings may !!!!!
     !!!!! have been disabled. Please restore any missing preprocess  !!!!!
     !!!!! and build steps manually in your app using the Rose GUI.   !!!!!
                           """
                self.add_report(info=warn_msg, is_warning=True)

        if steplist is not None or mirror_steplist is not None:
            # For each config type check if any steps are manually specified.
            keep = ''
            for key,value in ocean_steps.iteritems():

                # Remember which, if any, steps we find:
                if re.search(r"%s" % value, steps):
                    keep = keep + value + ' '

            # Now blank all except these:
            for key,value in ocean_steps.iteritems():
                if not re.search(r"%s" % value, keep):
                    atmos_steps[key] = ''

        # Now add the new variables:
        for key,value in ocean_steps.iteritems():
            self.add_setting(config, ["env", key], value)

        # Delete the old settings:
        self.remove_setting(config, ["env", "steplist"])
        self.remove_setting(config, ["env", "mirror_steplist"])

        return config, self.reports

class vn91_t6270(rose.upgrade.MacroUpgrade):

    BEFORE_TAG = "vn9.0_t6288"
    AFTER_TAG = "vn9.1"

    def upgrade(self, config, meta_config=None):
        """Upgrade configuration to next major version."""

        config_revision = self.get_setting_value(config, ['env', 'config_revision'])
        config_root = self.get_setting_value(config, ['env', 'config_root_path'])
        if config_root == '$SOURCE_UM_BASE':
            pass
        else:
            config_root = 'fcm:um_tr'
            config_revision = '@vn9.1'
            self.add_report('env', 'config_root_path', config_root, 
                info='Upgrading fcm_make config version to trunk@vn9.1',
                is_warning=True)
        self.change_setting_value(config, ['env', 'config_revision'], config_revision)
        self.change_setting_value(config, ['env', 'config_root_path'], config_root)

        # Ensure revision numbers are present:
        ocean_version = self.get_setting_value(config,
                        ["env", "ocean_version_file"])
        if not ocean_version:
            # Should exist, but here's the default:
            ocean_version = 'nemo3.2-cice4.1-version.cfg'

        if ocean_version == 'nemo3.2-cice4.1-version.cfg':
            nemo_rev = 'vn3.2'
            ioipsl_rev = 'vn3.0'
            cice_rev = 'vn4.1'
        else:
            nemo_rev = 'vn3.4'
            ioipsl_rev = 'vn3.4'
            cice_rev = 'vn4.1m1'

        self.add_setting(config, ["env", "nemo_rev"],   nemo_rev)
        self.add_setting(config, ["env", "ioipsl_rev"], ioipsl_rev)
        self.add_setting(config, ["env", "cice_rev"],   cice_rev)

        return config, self.reports

