import rose.upgrade
import re
import sys
from collections import defaultdict

class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__



class vn92_t1(rose.upgrade.MacroUpgrade):

    """Upgrade macro for ticket #1 by Paul Cresswell."""

    BEFORE_TAG = "vn9.2"
    AFTER_TAG = "vn9.2.1"

    def make_relative(self, project, sources):
        """Convert standard absolute paths into relative paths"""
        if project is 'IOIPSL':
            repos = 'NEMO'
        else:
            repos = project
        # Case-insensitive keywords:
        iproject = "(" + project + ")(?i)"
        sources = re.sub(r'fcm:'+iproject+'[-_](br)(?i)', 'branches', sources)
        sources = re.sub(r'fcm:'+iproject+'/branches',    'branches', sources)
        sources = re.sub(r'fcm:'+iproject+'[-_](tr)(?i)', 'trunk', sources)
        sources = re.sub(r'fcm:'+iproject+'/trunk',       'trunk', sources)
        # Met Office only:
        sources = re.sub(r'svn://fcm\d/'+repos+'_svn/'+project+'/', '',
                         sources)

        return sources

    def upgrade(self, config, meta_config=None):
        """Redirect fcm_make app to build from the mirrored configs"""
        warn_msg = ''
        config_root_path = self.get_setting_value(config, 
                           ["env", "config_root_path"])
        config_revision = self.get_setting_value(config,
                           ["env", "config_revision"])

        if re.match(r'\s*fcm:(um)(?i)[-_/]', config_root_path):
            config_root_path=re.sub(r'\s*fcm:(um)(?i)', 'fcm:um.xm',
                                    config_root_path)
            if not re.match(r'@(head)(?i)', config_revision):
                # Presumably not a branch, so:
                config_revision = '@vn9.2.1'            

        # Met Office only:
        elif re.match(r'\s*svn://fcm\d/UM_svn/UM', config_root_path):
            config_root_path=re.sub(r'\s*svn://fcm\d/UM_svn/UM','fcm:um.xm',
                                    config_root_path)
            if not re.match(r'@(head)(?i)', config_revision):
                # Presumably not a branch, so:
                config_revision = '@vn9.2.1'            

        # Last resort - set it to use the mirrored trunk.
        # If users need to edit this to use a branch, at least that's easy.
        else:
            if config_root_path != '$SOURCE_UM_BASE':
                config_root_path = 'fcm:um.xm_tr'
                config_revision  = '@vn9.2.1'
                warn_msg = """
  !!!!! WARNING: config_root_path has been reset to use the new trunk.
                           """

        # Does nothing if the value hasn't changed:
        self.change_setting_value(config, ["env", "config_root_path"],
                                  config_root_path)
        self.change_setting_value(config, ["env", "config_revision"],
                                  config_revision)

        # The new variables *_project_location mean we can simplify base and
        # source variables to use relative paths, without worrying about
        # inter-dependencies.

        # Needed for IOIPSL:
        version_file = self.get_setting_value(config,
                                              ["env", "ocean_version_file"])

        strings = [('NEMO', 'nemo_base'),     ('NEMO',   'nemo_sources'),
                   ('CICE', 'cice_base'),     ('CICE',   'cice_sources'),
                   ('IOIPSL', 'ioipsl_base'), ('IOIPSL', 'ioipsl_sources')]
        extracts = defaultdict(list)

        for key, value in strings:
            extracts[key].append(value)

        for projectname in extracts:
            basename   = extracts[projectname][0]   # e.g. 'nemo_base'
            sourcename = extracts[projectname][1]   # e.g. 'nemo_sources'

            # IOIPSL project/keyword varies by version (repos is always NEMO)
            if projectname == 'IOIPSL':
                repos = 'NEMO'
                if (version_file == 'nemo3.2-cice4.1-version.cfg'
                 or version_file is None):
                    # NEMO 3.2/default
                    project = 'IOIPSL'
                else:
                    # NEMO 3.4
                    project = 'NEMO'
            else:
                # For NEMO and CICE they're always the same:
                repos   = projectname    # e.g. 'NEMO'
                project = projectname    # e.g. 'NEMO'

            # Begin updating extract variables:
            # (*_base are compulsory=false variables)
            baseval = self.get_setting_value(config, ["env", basename])

            if baseval is not None:

                if (re.match(r'\s*fcm:('+project+'[-_/]tr)(?i)', baseval)
                 or re.match(r'\s*svn://fcm\d/'+repos+'_svn/'+project+'/trunk',
                             baseval)):
                    # trunk is the default, remove:
                    self.remove_setting(config, ["env", basename])
    
                elif (re.match(r'\s*(fcm:'+project+'[-_/]br)(?i)', baseval)
                   or re.match(r'\s*svn://fcm\d/'+repos+'_svn/'+project+'/branches',
                               baseval)):
                    # Keep branch, remove project:
                    baseval = self.make_relative(project, baseval)
                    self.change_setting_value(config, ["env", basename], baseval)
    
                elif re.match(r'\s*(fcm:|svn:|/)', baseval):
                    # Any remaining match is an unexpected keyword, URL or
                    # filepath. Don't second-guess; simply warn the user:
                    warn_msg = warn_msg + """
  !!!!! WARNING: %s may require attention.
                                          """ % basename

            # Allow everything to be specified by a relative path:
            # (*_sources are compulsory=true variables)
            sourcelist = self.get_setting_value(config, ["env", sourcename])
            sourcelist = self.make_relative(project, sourcelist)
            self.change_setting_value(config, ["env", sourcename], sourcelist)

            # Are there any non-standard URLs left that might need fixing?
            if re.search(r'(^| )(fcm:|svn:|/)', sourcelist):
                warn_msg = warn_msg + """
  !!!!! WARNING: %s may require attention.
                                      """ % sourcename

        # Print a general warning:
        warn_msg = """
  !!!!! All extract paths (nemo_base, nemo_sources, ioipsl_base, ioipsl_sources,
  !!!!! cice_base, cice_sources), unless including a full path to a project or
  !!!!! working copy, are now relative to the values of nemo_project_location,
  !!!!! ioipsl_project_location & cice_project_location.
  !!!!! A relative path is one specified relative to the project location URL,
  !!!!! e.g. nemo_sources=branches/dev/... instead of
  !!!!! nemo_sources=fcm:nemo_br/dev/...
  !!!!! You are advised to use relative paths where possible.
  !!!!!
  !!!!! Additionally, any value of nemo_base, ioipsl_base or cice_base referring
  !!!!! to that project's trunk can be removed, as this is the default in all 
  !!!!! cases.
                   """ + warn_msg
        self.add_report(info=warn_msg, is_warning=True)

        return config, self.reports


class vn100_t40(rose.upgrade.MacroUpgrade):

    BEFORE_TAG = "vn9.2.1"
    AFTER_TAG = "vn10.0"

    def upgrade(self, config, meta_config=None):
        """Upgrade configuration to next major version."""

        config_revision = self.get_setting_value(config, ['env', 'config_revision'])
        config_root = self.get_setting_value(config, ['env', 'config_root_path'])
        if config_root == '$SOURCE_UM_BASE':
            pass
        else:
            config_root = 'fcm:um.xm_tr'
            config_revision = '@vn10.0'
            self.add_report('env', 'config_root_path', config_root, 
                info='Upgrading fcm_make config version to trunk@vn10.0',
                is_warning=True)
        self.change_setting_value(config, ['env', 'config_revision'], config_revision)
        self.change_setting_value(config, ['env', 'config_root_path'], config_root)

        return config, self.reports

