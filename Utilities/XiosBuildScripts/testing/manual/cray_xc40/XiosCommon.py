'''
Common settings for XIOS for running manual tests
'''
class XiosCommonSettings(object):
    """
    Class for defining settings relating to XIOS needed for
    running build manually.
    """
    def __init__(self):
        """
        Initialise XIOS settings.
        """
        self.XIOS = 'XIOS'
        self.XIOS_MODULE_VERSION = '1.0'
        self.XIOS_PRGENV_VERSION = '1.0'
        self.XIOS_SRC_LOCATION_TYPE = 'URL'
        self.XIOS_REPO_URL = 'svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0'
        self.XIOS_REV = '684'

