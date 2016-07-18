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
'''
import unittest
import sys
import os
import mock

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))

import runtime_environment
runtime_environment.setup_env()
import testing_functions as func

import timer
import time


@timer.run_timer
def decorated_method(*args, **kwargs):
    '''Test method for run_timer decorator'''
    strings = [str(a) for a in args]
    return 'I am a decorated method: {}'.format('...'.join(strings))


class MyClass(object):
    '''Test class for run_timer decorator'''

    @timer.run_timer
    def decorated_class_method(*args, **kwargs):
        '''Test class method for run_timer decorator'''
        strings = [str(a) for a in args]
        return 'I am a decorated class method: {}'.format('...'.join(strings))


class PostProcTimerTests(unittest.TestCase):
    '''Unit tests for the PostProcTimer class'''
    def setUp(self):
        self.timer = timer.PostProcTimer()
        if 'init_timer' not in self.id():
            self.timer.timings = {'Method1': [1, 1, 1, 1],
                                  'Method3': [3, 3, 3, 3]}
            self.timer.timing_cache = {'Method1': 2.5,
                                       'Method2': 2.5}

    def teatDown(self):
        pass

    def test_init_timer(self):
        '''test timer object Instantiation'''
        func.logtest('Assert instantiation of a timer object:')
        self.assertIsInstance(self.timer, timer.PostProcTimer)
        self.assertEqual(self.timer.timings, {})
        self.assertEqual(self.timer.timing_cache, {})
        self.assertTrue(isinstance(self.timer.run_start, float))

    def test_start_timer(self):
        '''test start_timer method'''
        func.logtest('Assert functionality of start_timer method:')
        self.timer.start_timer('Label')
        self.assertTrue('Label' in self.timer.timing_cache.keys())

    @mock.patch('time.time', return_value=10.0)
    def test_end_timer_existing_func(self, mock_time):
        '''test end_timer method - existing method'''
        func.logtest('Assert functionality of end_timer - existing method:')
        self.timer.end_timer('Method1')
        self.assertEqual(self.timer.timings['Method1'], [8.5, 1, 7.5, 2])

    @mock.patch('time.time', return_value=10.0)
    def test_end_timer_new_func(self, mock_time):
        '''test end_timer method - new method'''
        func.logtest('Assert functionality of end_timer - new method:')
        self.timer.end_timer('Method2')
        self.assertEqual(self.timer.timings['Method2'], [7.5, 7.5, 7.5, 1])

    def test_check_timer_ok(self):
        '''test _check_timer_end method'''
        func.logtest('Assert functionality of check_timer_end method:')
        self.timer.timing_cache = {}
        self.timer._check_timer_end()
        self.assertNotIn('started a timer but not ended', func.capture('err'))

    def test_check_timer_problems(self):
        '''test _check_timer_end method - 2 methods in cache'''
        func.logtest('Assert 2 methods reported by check_timer_end method:')
        self.timer._check_timer_end()
        self.assertIn('started a timer but not ended', func.capture('err'))
        self.assertIn('Function Method1', func.capture('err'))
        self.assertIn('Function Method2', func.capture('err'))

    @mock.patch('time.time', return_value=100.0)
    def test_finalise_timer(self, mock_time):
        '''test finalise method'''
        func.logtest('Assert functionality of finalise method:')
        self.timer.finalise()
        meth1 = 'Method1                             1.00      1.00      '\
            '1.00      1.00         1'
        meth3 = 'Method3                             3.00      3.00      '\
            '3.00      1.00         3'
        self.assertIn(meth1, func.capture())
        self.assertNotIn('Method2', func.capture())
        self.assertIn(meth3, func.capture())
        mock_time.assert_called_once_with()


class TimerMethodsTests(unittest.TestCase):
    '''Unit tests for the timer module methods'''
    def setUp(self):
        if 'initialise' not in self.id():
            with mock.patch('timer.loadNamelist') as mock_nl:
                mock_nl.return_value.monitoring.ltimer = True
                timer.initialise_timer()

    def tearDown(self):
        for fname in runtime_environment.runtime_files:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_initialise_timer_null(self):
        '''test initialise_timer method - null instance'''
        func.logtest('Assert functionality of initialise_timer method - null:')
        timer.initialise_timer()
        self.assertIsInstance(timer.tim, timer.PostProcTimerNull)

    @mock.patch('timer.loadNamelist')
    def test_initialise_timer(self, mock_nl):
        '''test initialise_timer method'''
        func.logtest('Assert functionality of initialise_timer method:')
        mock_nl.return_value.monitoring.ltimer = True
        timer.initialise_timer()
        self.assertIsInstance(timer.tim, timer.PostProcTimer)

    @mock.patch('timer.PostProcTimer.finalise')
    def test_finalise_timer(self, mock_obj):
        '''test finalise_timer method'''
        func.logtest('Assert functionality of finalise_timer method:')
        timer.finalise_timer()
        mock_obj.assert_called_once_with()

    @mock.patch('timer.PostProcTimer.start_timer')
    def test_start_custom(self, mock_obj):
        '''test start_custom method'''
        func.logtest('Assert functionality of start_custom method:')
        timer.start_custom('Label')
        mock_obj.assert_called_once_with('custom_Label')

    @mock.patch('timer.PostProcTimer.end_timer')
    def test_end_custom(self, mock_obj):
        '''test end_custom method'''
        func.logtest('Assert functionality of end_custom method:')
        timer.end_custom('Label')
        mock_obj.assert_called_once_with('custom_Label')

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_single_arg(self, mock_start, mock_end):
        '''test run_timer method - single argument method'''
        func.logtest('Assert functionality of run_timer method - single arg:')
        rtn = decorated_method('arg1')
        mock_start.assert_called_once_with('decorated_method')
        mock_end.assert_called_once_with('decorated_method')
        self.assertEqual(rtn, 'I am a decorated method: arg1')

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_instance_arg(self, mock_start, mock_end):
        '''test run_timer method - single argument method'''
        func.logtest('Assert functionality of run_timer method - single arg:')
        rtn = decorated_method(MyClass())
        mock_start.assert_called_once_with('decorated_method')
        mock_end.assert_called_once_with('decorated_method')
        self.assertTrue(rtn.startswith('I am a decorated method: '))
        self.assertIn('<test_common_timer.MyClass object at', rtn)
        self.assertTrue(rtn.endswith('>'))

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_multi_arg(self, mock_start, mock_end):
        '''test run_timer method - multi argument method'''
        func.logtest('Assert functionality of run_timer method - multi arg:')
        rtn = decorated_method('arg1', 'arg2')
        mock_start.assert_called_once_with('decorated_method')
        mock_end.assert_called_once_with('decorated_method')
        self.assertEqual(rtn, 'I am a decorated method: arg1...arg2')

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_no_args(self, mock_start, mock_end):
        '''test run_timer method - no arguments method'''
        func.logtest('Assert functionality of run_timer method - no args:')
        rtn = decorated_method()
        mock_start.assert_called_once_with('decorated_method')
        mock_end.assert_called_once_with('decorated_method')
        self.assertEqual(rtn, 'I am a decorated method: ')

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_classmethod_arg1(self, mock_start, mock_end):
        '''test run_timer method - class method, single arg'''
        func.logtest('Assert functionality of run_timer - class method:')
        rtn = MyClass().decorated_class_method('arg1')
        label = 'MyClass.decorated_class_method'
        mock_start.assert_called_once_with(label)
        mock_end.assert_called_once_with(label)
        self.assertTrue(rtn.startswith('I am a decorated class method: '))
        self.assertIn('<test_common_timer.MyClass object at', rtn)
        self.assertTrue(rtn.endswith('...arg1'))

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_classmethod_arg2(self, mock_start, mock_end):
        '''test run_timer method - class method, multi arg'''
        func.logtest('Assert functionality of run_timer - class method:')
        rtn = MyClass().decorated_class_method('arg1', 'arg2')
        label = 'MyClass.decorated_class_method'
        mock_start.assert_called_once_with(label)
        mock_end.assert_called_once_with(label)
        self.assertTrue(rtn.startswith('I am a decorated class method: '))
        self.assertIn('<test_common_timer.MyClass object at', rtn)
        self.assertTrue(rtn.endswith('...arg1...arg2'))

    @mock.patch('timer.PostProcTimer.end_timer')
    @mock.patch('timer.PostProcTimer.start_timer')
    def test_runtimer_classmethod_no_args(self, mock_start, mock_end):
        '''test run_timer method - class method, no args'''
        func.logtest('Assert functionality of run_timer - class method:')
        rtn = MyClass().decorated_class_method()
        label = 'MyClass.decorated_class_method'
        mock_start.assert_called_once_with(label)
        mock_end.assert_called_once_with(label)
        self.assertTrue(rtn.startswith('I am a decorated class method: '))
        self.assertIn('<test_common_timer.MyClass object at', rtn)
        self.assertTrue(rtn.endswith('>'))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
