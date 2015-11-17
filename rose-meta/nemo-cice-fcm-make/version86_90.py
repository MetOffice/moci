import rose.upgrade
import fileinput
import os
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

class vn86_t5536(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #5536 by Paul Cresswell.
       Add the ability to use prebuilds in Rose."""
    
    BEFORE_TAG = "vn8.6"
    AFTER_TAG = "vn8.6_t5536"
    
    def upgrade(self, config, meta_config=None):
        """Upgrade a NEMO-CICE fcm-make app configuration."""
        # Add a prebuild variable (left blank for the user to select one):
        self.add_setting(config, ["env", "prebuild"], "")

        # Edit the fcm-make.cfg file to add the necessary 'use' statement:

        filename = './file/fcm-make.cfg'
        # Make sure the fcm-make.cfg file is available for upgrading:
        if not os.path.exists(filename):
            raise UpgradeError('Cannot find file/fcm-make.cfg, please apply this upgrade macro directly to the fcm_make app')

        # Insert the extra line:
        for line in fileinput.input([filename], inplace=True):
            if fileinput.isfirstline():
                line = 'use = $prebuild\n\n' + line
            sys.stdout.write(line)

        # No means yet of reporting changes in file/, so we provide our own:
        print '''\
[U] File upgrade %s-%s: 
    file=fcm-make.cfg
        Added text 'use = $prebuild'\
''' % (self.BEFORE_TAG, self.AFTER_TAG)

        return config, self.reports

class vn90_t5995(rose.upgrade.MacroUpgrade):

    BEFORE_TAG = "vn8.6_t5536"
    AFTER_TAG = "vn9.0"

    def upgrade(self, config, meta_config=None):
        """Upgrade configuration to next major version."""

        include = self.get_setting_value(config, ["env", "include_config"])
        if include.endswith('$SOURCE_UM_REV'):
           # Do nothing - this is a rose-stem-style fcm_make app
           pass
        else:
            include = re.sub(r'.*/fcm-make', r'fcm:um_tr/fcm-make', include)
            include = re.sub(r'@.*', r'@vn9.0', include)
            if '@' not in include:
                include = include + '@vn9.0'
            self.add_report("env", "include_config", include, 
             info="Upgrading fcm_make config version to trunk@vn9.0",
             is_warning=True)

        self.change_setting_value(config, ["env", "include_config"],
                                      include)

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

