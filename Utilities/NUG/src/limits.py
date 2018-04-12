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
    limits.py

DESCRIPTION
    Class limits of the production queues for a set of clusters

ENVIRONMENT VARIABLES
'''

from src.consumable import Consumable


class QueueSpec(object):
    ''' This object defines a limit set for a subproject
        on a queue on a cluster '''
    def __init__(self, subproject, cluster, queue, nodes):
        self.subproject = subproject
        self.cluster = cluster
        self.queue = queue
        self.nodes = nodes

    def __str__(self):
        return self.subproject + ' ' + self.cluster + ' ' + self.queue +\
               ' ' + str(self.nodes)

class LimitSets(object):
    ''' This object encapsulates a list of QueueSpec objects as defined by the
        limit file at initialisation '''
    def __init__(self, host_list, limits_file):
        inp = open(limits_file)
# read in the limit list and return a list of queuespecifications
        self.specs_list = []
        for line in inp:
            if 'subproject' in line:
                current_subproject = line.split(':')[1].strip()
            else:
                select_fields_list = line.split(':')
                clusterfield = \
                    [x for x in select_fields_list if 'cluster' in x]
                if clusterfield:
                    cluster = clusterfield[0].split('=')[1]
                    cluster.strip()
                queuefield = \
                    [x for x in select_fields_list if 'queue' in x]
                if queuefield:
                    queue = queuefield[0].split('=')[1]
                    queue.strip()
                nodefield = \
                    [x for x in select_fields_list if 'nodes' in x]
                if nodefield:
                    nodes = int(nodefield[0].split('=')[1].strip())

                if cluster in host_list:
                    queuespec = \
                        QueueSpec(current_subproject, cluster, queue, nodes)
                    self.specs_list.append(queuespec)

        inp.close()

    def nodes_limits(self, queue, subproject=None):
        ''' This method returns a node count for the total limits
            on a queue and a subproject. If the method is called without
            the subproject argument, it returns the total
            for all the subprojects.'''
        nodes = 0
        if subproject is None:
            for spec in self.specs_list:
                if spec.queue == queue:
                    nodes = nodes + spec.nodes
        else:
            for spec in self.specs_list:
                if (spec.subproject == subproject) and (spec.queue == queue):
                    nodes = nodes + spec.nodes

        return nodes

class ResourceSet(object):
    ''' This object is constructed from a Job List and a Limits set '''

    def __init__(self, job_list, limits):
        self.max_haswell = limits.nodes_limits('haswell')
        self.max_urgent = limits.nodes_limits('urgent')
        self.max_high = limits.nodes_limits('high')

        self.consumable_list = []
        for job in job_list.alljobs():
            if (job.queue in ['urgent', 'high', 'haswell']) and \
                any(consumable.subproject == \
                    job.subproject for consumable in self.consumable_list):
                for consumable in self.consumable_list:
                    if consumable.subproject == job.subproject:
                        if job.queue == 'urgent':
                            consumable.urgent = consumable.urgent +\
                                                job.nodes
                        elif job.queue == 'high':
                            consumable.high = consumable.high +job.nodes
                        elif job.queue == 'haswell':
                            consumable.haswell = consumable.haswell +\
                                                 job.nodes
            elif (job.queue in ['urgent', 'high', 'haswell']):
                new_consumable = Consumable(job.subproject, limits)
                if job.queue == 'urgent':
                    new_consumable.urgent = new_consumable.urgent +\
                                            job.nodes
                elif job.queue == 'high':
                    new_consumable.high = new_consumable.high +job.nodes
                elif job.queue == 'haswell':
                    new_consumable.haswell = new_consumable.haswell +\
                                              job.nodes
                self.consumable_list.append(new_consumable)

    def display_resource_set(self):
        '''For a job list display the resource sets associated with the list'''
        total_haswell = 0
        total_urgent = 0
        total_high = 0

        print '{0:<16}{1:<12}{2:<12}{3:<12}'.\
               format('PROJECT', 'HASWELL', 'URGENT', 'HIGH')
        for consumable in self.consumable_list:
            if isinstance(consumable, Consumable):
                print consumable
                total_haswell = total_haswell + consumable.haswell
                total_urgent = total_urgent + consumable.urgent
                total_high = total_high + consumable.high
        print ' '
        print 'TOTAL           %-12s%-12s%-12s' % (\
              '%-4s(%-4s)' % (str(total_haswell), str(self.max_haswell)), \
              '%-4s(%-4s)' % (str(total_urgent), str(self.max_urgent)), \
              '%-4s(%-4s)' % (str(total_high), str(self.max_high)), \
               )
