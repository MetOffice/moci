#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    consumable.py

DESCRIPTION
    defines a set of resources for the productions queues

ENVIRONMENT VARIABLES
'''

class Consumable(object):
    ''' This class contains the list of active nodes
        in the production queues and associated limits from the limit files '''
    def __init__(self, subproject, limits):
        self.subproject = subproject
        self.urgent = 0
        self.high = 0
        self.haswell = 0
        self.limit_urgent = limits.nodes_limits('urgent', self.subproject)
        self.limit_high = limits.nodes_limits('high', self.subproject)
        self.limit_haswell = limits.nodes_limits('haswell', self.subproject)

    def __str__(self):
        return '{0:<16}{1:<4d}({4:<4d})  {2:<4d}({5:<4d})  {3:<4d} ({6:4d})'\
              .format(self.subproject, self.haswell, \
                      self.urgent, self.high, self.limit_haswell,
                      self.limit_urgent, self.limit_high)
