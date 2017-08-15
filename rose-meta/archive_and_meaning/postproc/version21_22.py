import rose.upgrade
import re
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


class pp21_t194(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #194 by EricaNeininger."""
    BEFORE_TAG = "postproc_2.1"
    AFTER_TAG = "pp21_t194"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.add_setting(config,
                         ["namelist:suitegen", "process_toplevel",],
                         "true")
        self.add_setting(config,
                         ["namelist:suitegen", "archive_toplevel",],
                         "true")

        self.add_setting(config, ["namelist:suitegen", "ncks_path",], "")
        self.add_setting(config,
                         ["namelist:nemopostproc", "extract_region"], "false")
        self.add_setting(config,
                         ["namelist:nemopostproc", "region_dimensions"],
                         'x,1055,1198,y,850,1040')
        self.add_setting(config,
                         ["namelist:nemopostproc", "region_chunking_args"],
                         'time_counter/1,y/191,x/144')

        # Moving diagnostic namelist around
        fields = self.get_setting_value(config,
                                        ["namelist:nemoverify", "fields"])
        self.add_setting(config,
                         ["namelist:nemoverify", "meanfields"], fields)
        self.remove_setting(config,
                            ["namelist:nemoverify", "fields"])

        for model in ['nemo', 'cice']:
              work = self.get_setting_value(config,
                                            ["namelist:%spostproc" % model,
                                             "means_directory"])
              self.add_setting(config,
                               ["namelist:%spostproc" % model, "work_directory"],
                               work)
              self.remove_setting(config, ["namelist:%spostproc" % model,
                                           "means_directory"])

              compress = self.get_setting_value(config,
                                                ["namelist:%spostproc" % model,
                                                 "compress_means"])
              self.add_setting(config,
                               ["namelist:%spostproc" % model, "compress_netcdf"],
                               compress)
              self.remove_setting(config, ["namelist:%spostproc" % model,
                                           "compress_means"])

              # Update verification for concatenated streams due to change in syntax
              streams = self.get_setting_value(config,
                                               ["namelist:%sverify" % model, "meanstreams"])
              self.change_setting_value(config, ["namelist:%sverify" % model, "meanstreams"],
                                        streams.replace('_30','_1m'), forced=True)

        return config, self.reports

class pp21_t236(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #236 by Erica Neininger."""
    BEFORE_TAG = "pp21_t194"
    AFTER_TAG = "pp21_t236"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        cycle = self.get_setting_value(config,
                                       ["namelist:suitegen", "cycleperiod"])
        self.remove_setting(config, ["namelist:suitegen", "cycleperiod"])
        cycle = cycle.split(',')

        if cycle[0].startswith("$"):
            varname = cycle[0].strip("${}")
            try:
                cycle = self.get_setting_value(config, ["env", varname]).split(',')
                self.remove_setting_value(config, ["env", varname])

            except AttributeError:
                # Environment variable must be set in suite.rc
                # Get suite.rc file
                suitedir = os.getcwd()
                count = 0
                while "suite.rc" not in os.listdir(suitedir) and count < 5:
                      suitedir = os.path.dirname(suitedir)
                      count += 1

                newtext = ""
                with open(os.path.join(suitedir, "suite.rc"), "r") as suiterc:
                    text = suiterc.readlines()
                    for i, line in enumerate(text):
                        if line.strip().startswith(varname):
                            print 
                            try:
                                # Attempt to replace `rose date` command with simpler offset value
                                _, newval = re.split("--offset[12]?|-s |-1 |-2 ", line)
                                newval = newval.lstrip("=").split()[0]
                                text[i] = line.replace(line.split("=", 1)[-1],
                                                       " " + newval + "\n")
                            except ValueError:
                                  # `rose date --offset` not found
                                  # Original Y,M,D,h,m,s format will still work
                                  pass

                            break
                    newtext = ''.join(text)

                with open(os.path.join(suitedir, 'suite.rc'), 'w') as suiterc:
                    suiterc.write(newtext)

        if cycle[0].startswith("$"):
              setvalue = cycle[0]
        else:
            # Change incoming Y,M,D,h,m,s format to ISO data period
            setvalue = 'P'
            setvalue += ''.join([v + p for v, p in zip(cycle[:3], 'YMD') if int(v) > 0])
            if any([int(v) > 0 for v in cycle[3:]]):
                setvalue += 'T'
                setvalue += ''.join([v + p for v, p in zip(cycle[3:], 'HMS') if int(v) > 0])

        self.add_setting(config, ["env", "CYCLEPERIOD"], setvalue)

        return config, self.reports
