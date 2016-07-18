#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    timer.py

DESCRIPTION
    Timing routines for performance analysis of the post-processing code

'''
import time
import operator
import re
import utils
import inspect
from nlist import loadNamelist


def initialise_timer():
    '''
    Initalise the timer, and set up an instance of the timer class. There is
    a dummy instance for the case where the timer is not active.
    '''
    namelist = loadNamelist('monitorpp.nl')
    try:
        if namelist.monitoring.ltimer:
            timer_instance = PostProcTimer()
        else:
            timer_instance = PostProcTimerNull()
    except AttributeError:
        timer_instance = PostProcTimerNull()
    globals()['tim'] = timer_instance


def finalise_timer():
    '''
    Call the finalise method of the instance of the PostProcTimer class
    to avoid having instances of the class within the codebase.
    '''
    tim.finalise()


def start_custom(label):
    '''
    Start a custom timer at arbitary points within a function
    '''
    label = 'custom_{}'.format(label)
    msg = 'Starting custom timer {}'.format(label)
    utils.log_msg(msg, level=1)
    tim.start_timer(label)


def end_custom(label):
    '''
    End a custom timer at arbitary points within a function
    '''
    label = 'custom_{}'.format(label)
    msg = 'Ending custom timer {}'.format(label)
    utils.log_msg(msg, level=1)
    tim.end_timer(label)


def run_timer(function):
    '''
    This is the decorator function to apply to the functions that we wish
    to time, and provides human readable information about the location of
    these functions for the timing summary
    '''
    # Grab our calling frame. If the function to be timed is in a class,
    # 'class NAME' will appear in the string below. If the function is just
    # contained in a module, 'class NAME' will not appear.
    calling_frame = str((inspect.getouterframes(inspect.currentframe()))[2])
    if 'class' in calling_frame:
        classname = re.findall(r'class\s{1}([a-zA-Z_]{1}[a-zA-Z\d_]+)',
                               calling_frame)[0]
    else:
        classname = ''

    def wrapper(*args, **kw):
        '''
        Wrapper function for the function to be timed
        '''
        fn_label = function.__name__
        if classname:
            fn_label = '.'.join([classname, fn_label])
        tim.start_timer(fn_label)
        out = function(*args, **kw)
        tim.end_timer(fn_label)
        return out
    return wrapper


class PostProcTimerNull(object):
    '''
    This is a dummy timer object for the case where timing is inactive
    to ensure the instrumentation can remain in place, and nothing breaks
    '''

    def __init__(self, msg='Timer is not running'):

        utils.log_msg(msg, level=1)

    def start_timer(self, _):
        '''
        Dummy start_timer method
        '''
        pass

    def end_timer(self, _):
        '''
        Dummy end_timer method
        '''
        pass

    def finalise(self):
        '''
        Dummy finalise method
        '''
        pass


class PostProcTimer(PostProcTimerNull):
    '''
    Timing class to collate information and display a formatted summary at
    the end of the model run when finalise is called
    '''

    def __init__(self):

        PostProcTimerNull.__init__(self, msg='Timer is running')
        # The dictionary will contain a list of the total time, min time
        # max time and total number of calls to a particular routine
        self.timings = {}
        self.run_start = time.time()

        # Cache start times to allow for repeated calling of the module
        self.timing_cache = {}

    def start_timer(self, fnname):
        '''
        Initialise the timer for a given function
        '''
        self.timing_cache[fnname] = time.time()

    def end_timer(self, function_name):
        '''
        Ends the timing, and provides max, min, and average times if
        a function is called more than once
        '''
        end_time = time.time()
        total_time = end_time - self.timing_cache[function_name]
        self.timing_cache.pop(function_name)
        try:
            time_list = self.timings[function_name]
        except KeyError:
            time_list = [0, 1e10, 0, 0]
        time_list[0] += total_time
        time_list[1] = min(total_time, time_list[1])
        time_list[2] = max(total_time, time_list[2])
        time_list[3] += 1
        self.timings[function_name] = time_list

    def _check_timer_end(self):
        '''
        Ensure that all routines that have started a timer have also ended
        it. Alert the user if this isnt the case
        '''
        problem_functions = []
        for key in self.timing_cache:
            if key not in problem_functions:
                problem_functions.append(key)
                msg = 'Function {} has started a timer but' \
                    ' not ended it'.format(key)
                utils.log_msg(msg, level=3)

    def finalise(self):
        '''
        End the timing process, and display results to standard out
        '''
        run_end = time.time()
        run_length = run_end - self.run_start
        self._check_timer_end()
        # Get our list of functions in order of total time spent
        # This works as the total time is the first item in the list of
        # timing values
        sorted_fns = sorted(self.timings.items(),
                            key=operator.itemgetter(1), reverse=True)
        # write our output
        # prepare the headers
        summary = '\nTime between the timer initalise and finalise is' \
            ' {:.2f} seconds\n'.format(run_length)
        summary += '\nTIMING SUMMARY\n'
        summary += '{:>30}{:>10}{:>10}{:>10}{:>10}{:>10}\n'.format(
            'Function Name', 'Total', 'Min', 'Max', 'Average', 'Calls')
        summary += '-'*80+'\n'
        for func in sorted_fns:
            summary += '{:30.29}{:10.2f}{:10.2f}{:10.2f}{:10.2f}{:10d}\n'.\
                format(func[0],
                       self.timings[func[0]][0],
                       self.timings[func[0]][1],
                       self.timings[func[0]][2],
                       self.timings[func[0]][1] / self.timings[func[0]][3],
                       self.timings[func[0]][3])
        utils.log_msg(summary, level=1)
