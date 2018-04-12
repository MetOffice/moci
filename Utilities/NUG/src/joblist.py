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
    joblist.py

DESCRIPTION
    Class encapsulating a list of job objects

ENVIRONMENT VARIABLES
'''

import src.jobs
import os
import os.path

class JobList(object):
    ''' Class encapsulates a list of job objects.
        Most of the complexity is in the
        constructor that parses a qstat_snapshot data file '''
    def __init__(self, data_file='undefined'):
        self.job_list = []
        if (data_file != 'empty') and os.path.isfile(data_file):
            with open(data_file) as inp:
                for line in inp:
                    if 'Job Id' in line:
                        jobid = line.split(':')[1].strip()
                        self.job_list.append(src.jobs.Job(jobid))
                    if 'Account_Name' in line:
                        self.job_list[-1].project = line.split('=')[1].strip()
                    elif 'queue' in line:
                        if 'shared' in line:
                            queue = 'shared'
                            self.job_list[-1].queue = queue
                        elif 'normal' in line:
                            queue = 'normal'
                            self.job_list[-1].queue = queue
                        elif 'high' in line:
                            queue = 'high'
                            self.job_list[-1].queue = queue
                        elif 'urgent' in line:
                            queue = 'urgent'
                            self.job_list[-1].queue = queue
                        elif 'haswell' in line:
                            queue = 'haswell'
                            self.job_list[-1].queue = queue
                    elif 'job_state' in line:
                        self.job_list[-1].job_state = line.split('=')[1].strip()
                    elif 'ctime' in line:
                        self.job_list[-1].submission_time = \
                           line.split('=')[1].strip('\n')
                    elif 'Resource_List.walltime' in line:
                        time_string = line.split('=')[1].strip('\n')
                        hours, minutes, seconds = time_string.split(':')
                        self.job_list[-1].requested_time = \
                           int(hours)*3600+int(minutes)*60+int(seconds)
                    elif 'Resource_List.nodect' in line:
                        self.job_list[-1].nodes = \
                        int(line.split('=')[1].strip())
# This takes into account the MOM node so we remove 1
                        self.job_list[-1].nodes = self.job_list[-1].nodes-1
                    elif 'Job_Owner' in line:
                        tmp = line.split('=')[1].strip()
                        self.job_list[-1].user = tmp.split('@')[0].strip()
                    elif 'Resource_List.select' in line:
                        select_fields_string = line.split('=', 1)[1]
                        select_fields_list = select_fields_string.split(':')
                        nodefield = \
                        [x for x in select_fields_list if 'coretype' in x]
                        if nodefield:
                            self.job_list[-1].nodearch = \
                            nodefield[0].split('=')[1].strip()
                        subproject_field = \
                        [x for x in select_fields_list if 'subproject' in x]
                        if subproject_field:
                            self.job_list[-1].subproject = \
                             subproject_field[0].split('=')[1].rstrip('\n')

#   Now sort by queue
            decorated = [(job.queue, job) for job in self.job_list]
            decorated.sort()
            tmp_l = [job for queue, job in decorated]
            self.job_list = tmp_l

    def filtered(self, subproject_filter=None, user_filter=None,
                 account_filter=None, queue_filter=None):
        ''' Apply the job class filtering method to the whole list '''
        new_list = JobList()
        for job in self.job_list:
            if job.filter_conditions(subproject_filter, user_filter, \
                                     account_filter, queue_filter):
                new_list.append(job)
        return new_list

    def append(self, job):
        ''' Add a job to the list '''
        self.job_list.append(job)

    def __str__(self):
        ''' Display the list '''
        representation = ''
        for job in self.job_list:
            if isinstance(job, src.jobs.Job):
                representation = representation + job.__str__() +'\n'
        return representation

    def node_count(self):
        ''' Return the total number of nodes used by jobs in the job list '''
        total_nodes = 0
        for job in self.job_list:
            if isinstance(job, src.jobs.Job):
                total_nodes = total_nodes + job.nodes
        return total_nodes

    def alljobs(self):
        ''' Generator for the list of Jobs '''
        for job in self.job_list:
            yield job
