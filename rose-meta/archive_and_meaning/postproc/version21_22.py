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


class pp21_t221(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #221 by EricaNeininger."""
    BEFORE_TAG = "pp21_t236"
    AFTER_TAG = "pp21_t221"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        self.change_setting_value(config, ["file:nemocicepp.nl", "source"],
                                  "namelist:nemo_pp namelist:nemo_processing " +
                                  "namelist:nemo_archiving namelist:cice_pp " +
                                  "namelist:cice_processing namelist:cice_archiving " +
                                  "namelist:suitegen namelist:moose_arch")
        # NEMO/CICE common items
        for model in 'nemo', 'cice':
              for item in ["pp_run", "debug", "restart_directory", "work_directory"]:
                    self.rename_setting(config, ["namelist:%spostproc" % (model), item],
                                        ["namelist:%s_pp" % (model), item])

              for item in ["means_cmd", "base_component", "create_means",
                           "create_monthly_mean", "create_seasonal_mean",
                           "create_annual_mean", "create_decadal_mean",
                           "compress_netcdf", "compression_level", "chunking_arguments",
                           "correct_time_variables", "correct_time_bounds_variables",
                           "time_vars"]:
                    self.rename_setting(config, ["namelist:%spostproc" % (model), item],
                                        ["namelist:%s_processing" % (model), item])

              for item in ["archive_restarts", "archive_means", "means_to_archive"]:
                    self.rename_setting(config, ["namelist:%spostproc" % (model), item],
                                        ["namelist:%s_archiving" % (model), item])

              self.rename_setting(config, ["namelist:%spostproc" % (model),
                                           "archive_timestamps"],
                                           ["namelist:%s_archiving" % (model),
                                            "archive_restart_timestamps"])
              self.rename_setting(config, ["namelist:%spostproc" % (model),
                                           "buffer_archive"],
                                           ["namelist:%s_archiving" % (model),
                                            "archive_restart_buffer"])

        # NEMO only items
        for item in ["process_all_fieldsfiles"]:
              self.rename_setting(config, ["namelist:nemopostproc", item],
                                  ["namelist:nemo_pp", item])
 
        for item in ["msk_rebuild", "exec_rebuild", "exec_rebuild_icebergs",
                     "exec_rebuild_iceberg_trajectory", "ncatted_cmd",
                     "extract_region", "region_fieldsfiles", "region_dimensions",
                     "region_chunking_args", "means_fieldsfiles"]:
              self.rename_setting(config, ["namelist:nemopostproc", item],
                                  ["namelist:nemo_processing", item])

        self.rename_setting(config, ["namelist:nemopostproc", "rebuild_timestamps"],
                                     ["namelist:nemo_processing", "rebuild_restart_timestamps"])
        self.rename_setting(config, ["namelist:nemopostproc", "buffer_rebuild_rst"],
                                     ["namelist:nemo_processing", "rebuild_restart_buffer"])
        self.rename_setting(config, ["namelist:nemopostproc", "buffer_rebuild_mean"],
                                     ["namelist:nemo_processing", "rebuild_mean_buffer"])

        self.rename_setting(config, ["namelist:nemopostproc", "archive_iceberg_trajectory"],
                                     ["namelist:nemo_archiving", "archive_iceberg_trajectory"])

        # CICE only items
        self.rename_setting(config, ["namelist:cicepostproc", "cat_daily_means"],
                            ["namelist:cice_processing", "cat_daily_means"])

        self.remove_setting(config, ["namelist:nemopostproc"])
        self.remove_setting(config, ["namelist:cicepostproc"])

        return config, self.reports


class pp21_t238(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #238 by EricaNeininger."""
    BEFORE_TAG = "pp21_t221"
    AFTER_TAG = "pp21_t238"

    def upgrade(self, config, meta_config=None):
        """Add options for fieldsfile cut-out (mule_utils)"""
        self.add_setting(config,
                         ["namelist:atmospp", "streams_to_cutout",], "")        
        self.add_setting(config,
                         ["namelist:atmospp", "cutout_coords_type",], "indices")
        self.add_setting(config,
                         ["namelist:atmospp", "cutout_coords",], "1,1,192,145")

        return config, self.reports


class pp21_t265(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #265 by Erica Neininger."""
    BEFORE_TAG = "pp21_t238"
    AFTER_TAG = "pp21_t265"

    def upgrade(self, config, meta_config=None):
        """Upgrade a Postproc app configuration."""
        ffstreams = self.get_setting_value(config,
                                           ["namelist:atmosverify", "ff_streams"])
        if ffstreams:
            ffstreams = ','.join([f for f in ffstreams])  
            self.change_setting_value(config,
                                      ["namelist:atmosverify", "ff_streams"],
                                      ffstreams)

        return config, self.reports
