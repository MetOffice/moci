'''
*****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
*****************************COPYRIGHT******************************

Common settings for Oasis3-mct for running manual tests
'''
class OasisCommonSettings(object):
    """
    Class for defining settings relating to Oasis3-mct needed for
    running build manually.
    """
    def __init__(self):
        """
        Initialise Oasis3-mct settings.
        """
        self.OASIS3_MCT = 'oasis3-mct'
        self.OASIS_SRC_LOCATION_TYPE = 'URL'
        self.OASIS_REPO_URL = 'svn://fcm2/PRISM_svn/OASIS3_MCT/trunk/oasis3-mct'
        self.OASIS_REV_NO = '1343'
        self.OASIS_MAKE_REPO_URL = \
            'svn://fcm2/PRISM_svn/OASIS3_MCT/branches/dev/shaddad/' \
            'r1267_GC3_projOceanTutorial/oasis3-mct/util/make_dir/'
        self.OASIS_MAKE_REV_NO = '1327'
        self.OASIS_MAKE_FILE_NAME = 'make.cray_xc40_mo'
        self.OASIS_TUTORIAL_REPO_URL = \
            'fcm:moci.xm_br/dev/stephenhaddad/r379_XBS_externalOasisBuild/'\
            'Utilities/oasis3-mct_tutorial'
        self.OASIS_TUTORIAL_REV_NO = 'HEAD'
        self.OASIS_MODULE_VERSION = '1.0'
