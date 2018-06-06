#!/usr/bin/env python
"""
Script to generate a dashboard web page to monitor the MOCI nightly test suites.
The script interogates the cylc suite database of each test suite and present
an overview in tabular form.

Note: this script is written for python version 2.6, because this is the
version run by the www-hc web server.

"""
import os
import sqlite3
import ConfigParser
import datetime
import dateutil.parser

import sys

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
        # print 'opening databse {0}'.format(path_db)
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
    STATUS_SUBMITTED = 'submitted'
    STATUS_FAILED = 'failed'
    STATUS_RUNNING = 'running'
    STATUS_OTHER = 'other'

    HIGHLIGHT_COLOURS = {STATUS_SUCCEEDED: None,
                         STATUS_WAITING: '#FF7700',  # highlight orange
                         STATUS_FAILED: '#FF0000',  # highlight red
                         STATUS_RUNNING: '#00FF00',  # highlight green
                         STATUS_OTHER: '#FFFF00',  # highlight yellow
                        }

    def __init__(self,
                 title,
                 description,
                 path,
                 rose_bush_url,
                 family_list,
                 test_categories):
        """
        Initialiser function for a CylcDB object.
        :param suite_path: The path to the cylc-run directory of the suite.
        """
        self.title = title
        self.description = description
        self.suite_run_dir = path
        self.rose_bush_url = rose_bush_url
        path_db = os.path.join(self.suite_run_dir,
                               CylcDB.CYLC_DB_FNAME)
        self.test_categories = test_categories
        self.family_list = family_list
        SqlDatabase.__init__(self, path_db)

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
        if leaf_only:
            parent_tasks = \
                set(reduce(lambda x, y: x + y,
                           [t1[1].split(' ')[1:] for t1 in fts1]))
            family_task_list = [t1[0] for t1 in fts1
                                if family_name in t1[1] and t1[
                                    0] not in parent_tasks]
        else:
            family_task_list = [t1[0] for t1 in fts1 if family_name in t1[1]]
        return family_task_list

    def get_task_status_at_cycle(self, task, cycle):
        """
        Get the status of a cylc tasks at a particular cycle.
        :param task: The name of the task to query
        :param cycle: The cycle of the task to query
        :return: The statius of the task (a string)
        """
        columns = ['name', 'status', 'cycle']
        tsl1 = self.select_from_table(CylcDB.TNAME_TASK_STATES, columns)
        tsl1 = [(t1[2], t1[1]) for t1 in tsl1 if
                t1[2] == cycle and t1[0] == task]
        return tsl1

    def get_task_status_list(self, task):
        """
        Get a list of statuses for all tasks with the specified name.
        :param task: The name of the task to query
        :return: A list of task  statuses
        """
        columns = ['name', 'status', 'cycle']
        tsl1 = self.select_from_table(CylcDB.TNAME_TASK_STATES, columns)
        tsl1 = [t1[1] for t1 in tsl1 if t1[1] == task]
        return tsl1

    def get_family_task_status_list_at_cycle(self, family, cycle):
        """
        Get a list of statuses for all tasks in a specified family at
        the specified cycle.
        :param family: The name of the family to retrieve
        :param cycle: The cycle to retrieve family tasks at
        :return:A list of task statuses
        """
        ftl1 = self.get_tasks_in_family(family, True)
        columns = ['name', 'status', 'cycle']
        tsl1 = self.select_from_table(CylcDB.TNAME_TASK_STATES, columns)
        tsl1 = [(t1[0], t1[1]) for t1 in tsl1 if
                t1[0] in ftl1 and t1[2] == cycle]
        return tsl1

    def get_family_task_status_list(self, family):
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
        ftsl1 = self.get_family_task_status_list(family)
        summary1 = {CylcDB.STATUS_SUCCEEDED: sum(
            1 for t1 in ftsl1 if t1[2] == CylcDB.STATUS_SUCCEEDED),
                    CylcDB.STATUS_RUNNING: sum(
                        1 for t1 in ftsl1 if t1[2] == CylcDB.STATUS_RUNNING),
                    CylcDB.STATUS_FAILED: sum(
                        1 for t1 in ftsl1 if t1[2] == CylcDB.STATUS_FAILED),
                    CylcDB.STATUS_WAITING: sum(
                        1 for t1 in ftsl1 if
                        t1[2] in [CylcDB.STATUS_WAITING,
                                  CylcDB.STATUS_SUBMITTED]),
                    CylcDB.STATUS_OTHER: 0}
        summary1[CylcDB.STATUS_OTHER] = len(ftsl1) - sum(summary1.values())
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
        Create a summary table in html of the tasks in rach family of tasks
        in the family_list input argument.
        :param family_list: A list of task family names.
        :return: string - containing html table of summary of tasks in
                          each family
        """
        if not family_list:
            return ''

        html_output1 = '<table>\n'
        summary1 = self.get_family_task_summary(family_list[0])
        # add header row
        header_list1 = summary1.keys()
        header_html = '<tr><td>Task Family</td>'
        for cat1 in header_list1:
            link1 = self.rose_bush_url + '&task_status={0}'.format(cat1)
            cell_html = '<td><a href={url}>{name} </a></td>'
            cell_html = cell_html.format(name=cat1,
                                         url=link1)
            header_html += cell_html
        header_html += '</tr>\n'
        html_output1 += header_html

        for fam1 in family_list:
            summary1 = self.get_family_task_summary(fam1)

            row_html = '<tr><td>{0}</td>'.format(fam1)
            for cat1 in summary1.keys():
                if CylcDB.HIGHLIGHT_COLOURS[cat1] is not None and \
                                summary1[cat1] > 0:
                    row_html += \
                        '<td bgcolor={0}>{1:d}</td>'.format(
                            CylcDB.HIGHLIGHT_COLOURS[cat1],
                            summary1[cat1])
                else:
                    row_html += '<td >{0:d}</td>'.format(summary1[cat1])
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
        dt_list = [dateutil.parser.parse(dt1[0]) for dt1 in dt_list]
        start_datetime = min(dt_list)
        return start_datetime



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


def print_html_header():
    """
    Create a standard hml header.
    :return: A string containing a standard html header.
    """
    dt_str = DT_STR_TEMPLATE.format(dt=datetime.datetime.now())
    time_gen_str = '<p>Dashboard generated at {0}</p><br>'.format(dt_str)

    print 'Content-Type: text/html;charset=utf-8\n'
    print '''<html>\n \
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<head>
    <title> MOCI test suite dashboard</title>
    <link rel="stylesheet" type="text/css" href="dashboard.css">
</head>

<body>

        \n'


<div class="row">
    <div class="header_logo_cell">
        <a href="http://www.metoffice.gov.uk" target="_blank" title="opens in a new window"><img src="http://www.metoffice.gov.uk/lib/template/logos/MO_Master_W.jpg" alt="Met Office" title="www.metoffice.gov.uk" width="120" height="109" /></a>
    </div>
    <div class="header_text_cell">
        <h1> MOCI test suite dashboard </h1>
        {time_gen_str}
    </div>
    <div class="header_logo_cell">
         <a href="http://code.metoffice.gov.uk/trac/moci"><img src="moci_logo_small.png" title="MOCI"/></a>
    </div>
</div>


'''.format(time_gen_str=time_gen_str)

def read_config(conf_path):
    """
    Read in the config info for the dashboard page.
    :param conf_path: The path to the config file.
    :return: A dictionary with the details of all the suites to report on.
    """
    dash_parser = ConfigParser.ConfigParser()
    dash_parser.read(conf_path)

    cylc_run_path = dash_parser.get('base', 'cylc_run_path')

    suite_sections = [s1 for s1 in dash_parser.sections() if 'base' != s1]
    dash_dict = {}
    for suite1 in suite_sections:
        suite_dict1 = dict(dash_parser.items(suite1))
        try:
            suite_dict1['family_list'] = suite_dict1['family_list'].split(',')
        except KeyError:
            suite_dict1['family_list'] = []
        try:
            suite_dict1['test_categories'] = \
                suite_dict1['test_categories'].split(',')
        except KeyError:
            suite_dict1['test_categories'] = []

        suite_dict1['path'] = os.path.join(cylc_run_path, suite1)
        dash_dict[suite1] = suite_dict1


    return dash_dict


def main():
    """
    The main function for this module.
    """
    print_html_header()

    try:
        conf_path = os.environ['MOCI_DASH_CONF_PATH']
    except KeyError:
        conf_path = 'moci_dashboard.conf'

    dash_dict = read_config(conf_path)
    for suite1 in dash_dict.keys():
        try:
            cdb1 = CylcDB(**dash_dict[suite1])
            print(cdb1.to_html())

        except:
            # no exception type specified as whatever the error,
            # I want the dashboard to report an error for that suite and
            # continue looking at the other suites.
            print('<br><b><font color=red>ERROR: test suite output '
                  'not found or corrupt.</font></b><br>')
        print('</div>\n')


if __name__ == '__main__':
    main()

