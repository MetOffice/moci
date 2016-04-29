'''
*****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
*****************************COPYRIGHT******************************

Common settings for NEMO for running manual tests
'''
class NemoCommonSettings(object):
    """
    Class for defining settings relating to NEMO needed for
    running build manually.
    """
    def __init__(self):
        """
        Initialise NEMO settings.
        """
        self.NEMO = 'NEMO'
