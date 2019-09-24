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
    jobs.py

DESCRIPTION
    class encapsulating information about a single PBS job on the
    Met Office Cray XC40 systems

ENVIRONMENT VARIABLES
'''

import pwd
from datetime import datetime

class Job(object):
    ''' defines a PBS Job'''
    def __init__(self, jobid):
# Type string
        self.jobid = jobid
        self.settings = []
        self.user = 'unknown'
        self.project = 'unknown'
        self.queue = 'unknown'
        self.job_state = 'Q'
        self.nodearch = 'haswell'
        self.subproject = 'default'
# Type string / unit times
        self.submission_time = 'unknown'
# Type integer
        self.cores = 0
        self.nodes = 0
# Type integer / unit seconds
        self.requested_time = '0'
        self.queue_time = -1
# Type real / unit percentage/ratio
        self.queueing_ratio = 0

    def is_climate(self):
        """ is the job a climate job """
        return self.project == 'climate'

    def owner(self):
        """ return the owner (real name) of the job """
        if self.user == 'fpos2' or self.user == 'fpostest' \
            or self.user == 'fpos1':
            user = 'opsuite'
        else:
            user = pwd.getpwnam(self.user)[4]
        return user+'('+self.user+')'

    def is_running(self):
        """ Return True if job in Running state """
        return self.job_state == 'R'

    def is_compute(self):
        """ Return True if job is a Compute job (ie not 'shared') """
        return self.queue != 'shared'

    def is_high_priority(self):
        """ Return True if job is in high priority queue """
        return (self.queue == 'high') or (self.queue == 'urgent')

    def ratio_queuing(self):
        """ Return a percentage of queueing time compared to requested """

    def calculate_queue_time(self):
        """ return integer : seconds between global job submission
            and program time """
# input: submission time in C time format string
        program_time = datetime.now()
        fmtin = ' %a %b %d %H:%M:%S %Y'
        submit_time = datetime.strptime(self.submission_time, fmtin)
        delta = program_time-submit_time
        total_seconds = delta.days*24*3600+delta.seconds
        self.queue_time = total_seconds

    def __str__(self):
        """ standard output display routine """
        if self.is_running():
            return 'R:%s: %-20s%-4s nodes %s %s' % (self.jobid, \
                '%s(%s)' % (self.project, self.subproject), \
                self.nodes, \
                self.queue, \
                self.owner())
        else:
            self.calculate_queue_time()
            ratio = 100*float(self.queue_time)/float(self.requested_time)
            return 'Q:%s: %-20s%-4s nodes %s %s queued  \
                    for %8.0fs (%4.2f%% of req)' % (self.jobid, \
                '%s(%s)' % (self.project, self.subproject), \
                self.nodes, \
                self.queue, \
                self.owner(), \
                self.queue_time, \
                ratio)

    def filter_conditions(self, subproject_filter=None, user_filter=None, \
                          account_filter=None, queue_filter=None,
                          job_state_filter=None):
        """ this method test if a job belongs to a list of subprojects,
            users, account or queues. If one of the four attributes
            is not specified the condition is considered True. """
        subproject_condition = (not subproject_filter) or \
            (subproject_filter and \
                 self.subproject in subproject_filter)

        user_condition = (not user_filter) or \
            (user_filter and self.user in user_filter)

        account_condition = (not account_filter) or \
            (account_filter and self.project in account_filter)

        queue_condition = (not queue_filter) or \
            (queue_filter and self.queue in queue_filter)

        job_state_condition = (not job_state_filter) or \
            (job_state_filter and \
                 self.job_state in job_state_filter)

        return subproject_condition and user_condition and account_condition \
            and queue_condition and job_state_condition
