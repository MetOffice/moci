#!/usr/bin/env python
"""
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_suite_dashboard.py

DESCRIPTION
    Generate a dashboard web page to monitor a suite of tests.
    The script interogates the cylc suite database of each test suite
    and present an overview in tabular form.

    Please note: This script is compatibile with Python3, however it
                 MUST be backwards compatible because the www-hc web server
                 currently runs Python2.6.
"""

import sys
import os
import re
import sqlite3
import configparser
from functools import reduce

import datetime
import pytz


DT_STR_TEMPLATE = \
    '{dt.year}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}'

class SqlDatabase(object):
    """
    Class to represent a general sqlite database.
    """
    def __init__(self, path_db):
        """
        Initialiser function for SQL_DB class.
        :param path_db: path to the database file
        """
        self.path_db = path_db
        self.db_connection = sqlite3.connect(path_db)
        self.db_cursor = self.db_connection.cursor()

    def __del__(self):
        """
        Class to clean up database connection when SQL_DB object is destroyed
        """
        if self.db_cursor:
            self.db_cursor.close()
        if self.db_connection:
            self.db_connection.close()

    def select_from_table(self, table_name, columns):
        """
        Select items from the table of the database.
        :param table_name: The name of the table to select from.
        :param columns: The name of columns to select
        :return: The items from the select call.
        """
        columns_str = ','.join(columns)
        db_cmd1 = 'SELECT {columns} FROM {table_name};'
        db_cmd1 = db_cmd1.format(columns=columns_str,
                                 table_name=table_name)
        self.db_cursor.execute(db_cmd1)
        results1 = self.db_cursor.fetchall()
        return results1


class CylcDB(SqlDatabase):
    """
    A class to encapsulate a cylc suite database.
    """
    TNAME_TASK_STATES = 'task_states'
    TNAME_INHERIT = 'inheritance'
    CYLC_DB_FNAME = 'cylc-suite.db'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_WAITING = 'waiting'
    STATUS_QUEUED = 'queued'
    STATUS_READY = 'ready'
    STATUS_SUBMITTED = 'submitted'
    STATUS_FAILED = 'failed'
    STATUS_RUNNING = 'running'
    STATUS_OTHER = 'other'
    STATUS_HELD = 'held'
    STATUS_RETRY = 'retrying'

    HIGHLIGHT_COLOURS = {STATUS_SUCCEEDED: '#FFFFFF', # No highlight
                         STATUS_WAITING: '#FF7700',  # highlight orange
                         STATUS_FAILED: '#FF0000',  # highlight red
                         STATUS_RUNNING: '#00FF00',  # highlight green
                         STATUS_OTHER: '#FFFF00',  # highlight yellow
                         'SummaryBar': '#DDDEE5',  # Highlight grey
                        }

    def __init__(self,
                 title,
                 description,
                 cylc_run_path,
                 rose_bush_url,
                 family_list,
                 test_categories,
                 test_frequency):
        """
        Initialiser function for a CylcDB object.
        :param suite_path: The path to the cylc-run directory of the suite.
        """
        suite_name = os.path.basename(cylc_run_path)
        if suite_name.startswith(title):
            self.title = suite_name
        else:
            self.title = title
        self.description = description
        self.suite_run_dir = cylc_run_path
        self.rose_bush_url = rose_bush_url
        path_db = os.path.join(self.suite_run_dir,
                               CylcDB.CYLC_DB_FNAME)
        self.test_categories = test_categories
        self.family_list = family_list
        try:
            test_freq_hrs = re.match(r'^(\d*)[dD]', test_frequency).group(1)
            test_freq_hrs = int(test_freq_hrs) * 24
        except AttributeError:
            test_freq_hrs = re.match(r'^(\d*)[hH]?', test_frequency).group(1)
        self.test_freq_hrs = int(test_freq_hrs)

        SqlDatabase.__init__(self, path_db)


    def suite_date_valid(self, start_dt_str):
        '''
        Takes the suite start date and ensure it has run within the
        past <self.test_freq_hrs> hours.
        Returns True if true, False if not
        '''
        past_hrs = datetime.datetime.now() - \
                   datetime.timedelta(hours=self.test_freq_hrs)
        past_hrs = DT_STR_TEMPLATE.format(dt=past_hrs)
        return start_dt_str > past_hrs

    def get_tasks_in_family(self, family_name, leaf_only):
        """
        Retrieve a list of all the tasks in a family with the specified name.
        :param family_name: Name of the family of tasks to retrieve.
        :param leaf_only: If leaf_only is True, then tasks which other tasks
                          inherit
        :return: list of tasks in the family.
        """
        columns = ['namespace', 'inheritance']
        fts1 = self.select_from_table(CylcDB.TNAME_INHERIT, columns)

        # look for tasks that inherit from the parent task. If we are looking
        # for "leaf" tasks only (i.e. tasks that are actually executed) we want
        # to exclude all tasks that are inherited from, as usually tasks that
        # are run are not inherited from.

        # Pre-filter for family name because reduce is expensive
        fts1 = [t1 for t1 in fts1 if family_name in t1[1]]
        if leaf_only:
            parent_tasks = \
                set(reduce(lambda x, y: x + y,
                           [t1[1].split(' ')[1:] for t1 in fts1]))
            fts1 = [t1 for t1 in fts1 if t1[0] not in parent_tasks]
        return [t1[0] for t1 in fts1]

    def get_family_task_status(self, family):
        """
        Get a list of statuses for all tasks in a specified family.
        :param family: The name of the family to retrieve
        :return:A list of task statuses
        """
        ftl1 = self.get_tasks_in_family(family, True)
        columns = ['name', 'status', 'cycle']
        tsl1 = self.select_from_table(CylcDB.TNAME_TASK_STATES, columns)
        # select tasks in family
        tsl1 = [(t1[0], t1[2], t1[1]) for t1 in tsl1 if t1[0] in ftl1]

        # filter out tasks in list that are after the final cycle but have
        # been included because of the run ahead limit.
        task_list1 = self.select_from_table('task_jobs', ['name', 'cycle'])
        tsl1 = [t1 for t1 in tsl1 if t1[0:2] in task_list1]

        return tsl1

    def get_family_task_summary(self, family):
        """
        Get a summary of how many tasks in a family are in each status
        category. E.g. 4 succeeded, 2 runnning, 1 failed. The results
        are return as a dictionary.
        :param family: The family name
        :return: A dictionary with the number of tasks from the specified
                 family in each status category.
        """
        summary1 = {
            CylcDB.STATUS_SUCCEEDED: 0,
            CylcDB.STATUS_RUNNING: 0,
            CylcDB.STATUS_FAILED: 0,
            CylcDB.STATUS_WAITING: 0,
            CylcDB.STATUS_OTHER: 0,
        }
        for _, _, status in self.get_family_task_status(family):
            try:
                summary1[status] += 1
            except KeyError:
                if status in [CylcDB.STATUS_SUBMITTED,
                              CylcDB.STATUS_READY,
                              CylcDB.STATUS_QUEUED]:
                    summary1[CylcDB.STATUS_WAITING] += 1
                else:
                    summary1[CylcDB.STATUS_OTHER] += 1
        return summary1

    def create_summary_list(self, family_list):
        """
        Create a summary in html of the pass/fail status of each of the
        families of tasks in the family_list input.
        :param family_list: The list of families to create summaries for.
        :return: A string containing html of the summaries.
        """
        if not family_list:
            return ''
        html_output1 = '<p>\n'
        for fam1 in family_list:
            summary1 = self.get_family_task_summary(fam1)
            total1 = sum(summary1.values())
            if total1 > 0:
                html_output1 += '{0}: '.format(fam1)
                if summary1[CylcDB.STATUS_FAILED] > 0:
                    status_html = '<fail>Failed</fail>'
                    stat_txt = 'Failed'
                elif summary1[CylcDB.STATUS_SUCCEEDED] == total1:
                    status_html = '<succeed>Succeeded</succeed>'
                    stat_txt = 'Succeeded'
                else:
                    status_html = '<other>Other</other>'
                    stat_txt = 'Other'

                html_output1 += status_html + '<br>\n'
                sys.stderr.write('{0} - {1}\n'.format(fam1, stat_txt))
        html_output1 += '</p>\n'
        return html_output1

    def create_summary_table(self, family_list):
        """
        Create a summary table in html of the tasks in each family of tasks
        in the family_list input argument.
        :param family_list: A list of task family names.
        :return: string - containing html table of summary of tasks in
                          each family
        """
        if not family_list:
            return ''

        row_fmt = '<td bgcolor={col}>{name}</td>'

        html_output1 = '<table>\n'
        summary1 = self.get_family_task_summary(family_list[0])
        # add header row
        header_list1 = summary1.keys()
        header_html = '<tr>' + row_fmt.format(
            col=CylcDB.HIGHLIGHT_COLOURS['SummaryBar'],
            name='Task Family'
        )
        for cat1 in header_list1:
            statuses = [cat1]
            if cat1 == CylcDB.STATUS_WAITING:
                statuses.append(CylcDB.STATUS_QUEUED)
                statuses.append(CylcDB.STATUS_READY)
                statuses.append(CylcDB.STATUS_SUBMITTED)
            elif cat1 == CylcDB.STATUS_OTHER:
                statuses.append(CylcDB.STATUS_HELD)
                statuses.append(CylcDB.STATUS_RETRY)
                statuses.append('submit-' + CylcDB.STATUS_RETRY)
                statuses.append('submit-' + CylcDB.STATUS_FAILED)
            link1 = self.rose_bush_url.replace('cycles', 'taskjobs')
            for status in statuses:
                link1 += '&task_status={0}'.format(status)

            cell_html = row_fmt.format(
                col=CylcDB.HIGHLIGHT_COLOURS['SummaryBar'],
                name='<a href={url}>{cat} </a>'.format(url=link1, cat=cat1)
            )
            header_html += cell_html
        header_html += '</tr>\n'
        html_output1 += header_html

        for fam1 in family_list:
            summary1 = self.get_family_task_summary(fam1)
            if fam1 == '':
                fam1 = '~~~ ALL tasks'
                cell_col = 'SummaryBar'
            else:
                cell_col = CylcDB.STATUS_SUCCEEDED
            row_html = '<tr>' + row_fmt.format(
                col=CylcDB.HIGHLIGHT_COLOURS[cell_col],
                name=fam1
            )

            for cat1 in summary1.keys():
                shade = cell_col
                if summary1[cat1] > 0 and cat1 != CylcDB.STATUS_SUCCEEDED:
                    shade = cat1
                row_html += row_fmt.format(
                    col=CylcDB.HIGHLIGHT_COLOURS[shade],
                    name=summary1[cat1]
                )
            row_html += '</tr>\n'
            html_output1 += row_html
        html_output1 += '</table>\n'
        return html_output1

    def to_html(self):
        """
        Create an html summary of the status of the suite represented by
        this cylc suite database.
        :return: A string containing html summarising the status of the suite.
        """
        sys.stderr.write('producing output for {0}\n'.format(self.title))
        html_output1 = ''
        html_output1 += '<div class="row">\n'
        html_output1 += '<h2>{0}</h2><br>\n'.format(self.title)

        html_output1 += '</div><div class="row">\n'

        html_output1 += '    <div class="column">\n'
        try:
            html_output1 += '<p>{0}<br>\n'.format(self.description)
        except KeyError:
            html_output1 += '<p>\n'
        html_output1 += '\n<a href={0}>Rose bush output</a><br>\n'.format(
            self.rose_bush_url)
        start_dt_str = \
            DT_STR_TEMPLATE.format(dt=self.get_suite_start_time())
        html_output1 += 'suite started at {0}<br>\n'.format(start_dt_str)
        lastsubmit_dt_str = \
            DT_STR_TEMPLATE.format(dt=self.get_suite_lastsubmit_time())
        html_output1 += 'suite last submitted a task at {0}<br>\n'.format(
            lastsubmit_dt_str
        )
        if not self.suite_date_valid(lastsubmit_dt_str):
            html_output1 += '<b><font color="red"> Warning </font>'
            html_output1 += 'This suite has not submitted a task in the past '
            html_output1 += str(self.test_freq_hrs)
            html_output1 += ' hours. Please investigate</b><br>\n'
        html_output1 += \
        self.create_summary_list(self.test_categories)
        html_output1 += '</p>\n'
        html_output1 += '    </div>\n'
        html_output1 += '    <div class="column">\n'
        html_output1 += \
            self.create_summary_table(self.family_list)
        html_output1 += '    </div>\n'
        return html_output1

    def get_suite_start_time(self):
        """
        Get the time of the first task submission for a suite.
        :return: A python datetime object with the submission time of the
                 first task submitted.
        """
        dt_list = self.select_from_table('task_events', ['time'])
        dt_list = [self._parse_date(dt1[0]) for dt1 in dt_list]
        start_datetime = min(dt_list)
        return start_datetime

    def get_suite_lastsubmit_time(self):
        """
        Get the time of the last task submission for a suite.
        :return: A python datetime object with the submission time of the
                 first task submitted.
        """
        dt_list = self.select_from_table('task_events', ['time'])
        dt_list = [self._parse_date(dt1[0]) for dt1 in dt_list]
        lastsubmit_datetime = max(dt_list)
        return lastsubmit_datetime

    @staticmethod
    def _parse_date(value):
        """Custom date parser which assumes UTC.
        :param value: An iso format string.
        :return A python datetime object.
        """

        return datetime.datetime(int(value[:4]), int(value[5:7]),
                                 int(value[8:10]), int(value[11:13]),
                                 int(value[14:16]), int(value[17:19]),
                                 tzinfo=pytz.UTC)


def create_html_table(table1):
    """
    Create a html table from a a list of lists of strings
    :param table1: a list of lists, with each item in the root lists a string.
    :return: A string containing an html table with the data from table1.
    """
    html_output1 = '<table>\n'
    for row1 in table1:
        html_output1 += '<tr> '
        for column1 in row1:
            html_output1 += '<td> {0} </td>'.format(column1)
        html_output1 += '</tr> \n'
    html_output1 += '</table>\n'
    return html_output1


def print_html_header(logo_file, wiki_url):
    """
    Create a standard hml header.
    :return: A string containing a standard html header.
    """
    dt_str = DT_STR_TEMPLATE.format(dt=datetime.datetime.now())
    time_gen_str = '<p>Dashboard generated at {0}</p><br>'.format(dt_str)

    print('Content-Type: text/html;charset=utf-8\n')
    print('''<html>\n \
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<head>
    <title> Test Suite Dashboard</title>
    <link rel="stylesheet" type="text/css" href="dashboard.css">
</head>
 <body>

         \n'


<div class="row">
    <div class="header_logo_cell">
        <a href="http://www.metoffice.gov.uk" target="_blank" title="opens in a new window"><img src="http://www.metoffice.gov.uk/lib/template/logos/MO_Master_W.jpg" alt="Met Office" title="www.metoffice.gov.uk" width="120" height="109" /></a>
    </div>
    <div class="header_text_cell">
        <h1> Test Suite Dashboard</h1>
        {time_gen_str}
    </div>
    <div class="header_logo_cell">
         <a href="{wiki}"><img src="{logo}" title="LOGO" width="350"/></a>
    </div>
</div>


'''.format(time_gen_str=time_gen_str, wiki=wiki_url, logo=logo_file))

def read_config(conf_path):
    """
    Read in the config info for the dashboard page.
    :param conf_path: The path to the config file.
    :return: A dictionary with the details of all the suites to report on.
    """
    dash_parser = configparser.ConfigParser()
    dash_parser.read(conf_path)

    cylc_run_path = dash_parser.get('base', 'cylc_run_path')
    rose_bush_base_url = dash_parser.get('base', 'rose_bush_base_url')
    logo_file = dash_parser.get('base', 'logo_file')
    wiki_url = dash_parser.get('base', 'wiki_url')

    suite_sections = [s1 for s1 in dash_parser.sections() if 'base' != s1]
    dash_dict = {}
    for suite1 in suite_sections:
        if suite1.startswith("!"):
            continue
        test_dict1 = dict(dash_parser.items(suite1))
        test_dict1['family_list'] = test_dict1.get('family_list',
                                                   '').split(',')
        test_dict1['test_categories'] = test_dict1.get('test_categories',
                                                       '').split(',')
        test_avail = False
        for test1 in os.listdir(cylc_run_path):
            if re.match(suite1 + r'(_\d{4}-\d{2}-\d{2})?$', test1):
                test_dict1['cylc_run_path'] = os.path.join(cylc_run_path, test1)
                test_dict1['rose_bush_url'] = rose_bush_base_url + test1

                dash_dict[test1] = test_dict1
        if not test_avail:
            # No test available in  cylc_runs - add default to flag the loss
            dash_dict[suite1] = test_dict1

    return dash_dict, logo_file, wiki_url


def main():
    """
    The main function for this module.
    """
    try:
        conf_path = os.environ['DASH_CONF_PATH']
    except KeyError:
        conf_path = 'dashboard.conf'

    dash_dict, logo_file, wiki_url = read_config(conf_path)

    print_html_header(logo_file, wiki_url)

    html_output = {}
    for suite1 in sorted(dash_dict.keys()):
        try:
            cdb1 = CylcDB(**dash_dict[suite1])
            html_output['{}_{}'.format(cdb1.get_suite_start_time(),
                                       suite1)] = cdb1.to_html()
        except:
            # no exception type specified as whatever the error,
            # I want the dashboard to report an error for that suite and
            # continue looking at the other suites.
            print('<br><b><font color=red>ERROR: test suite output {0} '
                  'not found or corrupt.</font></b><br>'.format(suite1))
            print('</div>\n')

    for _, suite_html1 in reversed(sorted(html_output.items())):
        print(suite_html1)
        print('</div>\n')


if __name__ == '__main__':
    main()
