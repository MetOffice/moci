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
    STATUS_FAILED = 'failed'
    STATUS_RUNNING = 'running'
    STATUS_OTHER = 'other'

    def __init__(self, suite_path):
        """
        Initialiser function for a CylcDB object.
        :param suite_path: The path to the cylc-run directory of the suite.
        """
        self.suite_run_dir = suite_path
        path_db = os.path.join(self.suite_run_dir,
                               CylcDB.CYLC_DB_FNAME)
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
        tsl1 = [(t1[0], t1[2], t1[1]) for t1 in tsl1 if t1[0] in ftl1]
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
                        1 for t1 in ftsl1 if t1[2] == CylcDB.STATUS_WAITING),
                    CylcDB.STATUS_OTHER: 0}
        summary1[CylcDB.STATUS_OTHER] = len(ftsl1) - sum(summary1.values())
        return summary1

    def get_suite_start_time(self):
        """
        Get the time of the first task submission for a suite.
        :return: A python datetime object with the submission time of the
                 first task submitted.
        """
        dt_list = self.select_from_table('task_events',['time'])
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
    print 'Content-Type: text/html;charset=utf-8\n'
    print '''<html>\n \
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <head>
        <title> MOCI test suite dashboard</title>
    </head>
    <style>
    table, td, th {
        border: 1px solid green;
    }

    th {
        background-color: green;
        color: white;
    }
    </style>
    <body>
    '''

    dt_str = DT_STR_TEMPLATE.format(dt=datetime.datetime.now())
    print '<p>Dashboard generated at {0}</p><br>'.format(dt_str)


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
        suite_dict1['family_list'] = suite_dict1['family_list'].split(',')
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

    # for suite1, desc1, fam_list1, url1 in CYLC_SUITE_LIST:
    for suite1 in dash_dict.keys():
        print('<h1>{0}</h1>\n'.format(dash_dict[suite1]['title']))

        try:
            suite_path = dash_dict[suite1]['path']
            cdb1 = CylcDB(suite_path)

            start_dt_str = \
                DT_STR_TEMPLATE.format(dt=cdb1.get_suite_start_time())
            print 'suite started at {0}<br>'.format(start_dt_str)

            html_output1 = '<a href={0}>Rose bush output</a>'.format(
                dash_dict[suite1]['rose_bush_url'])
            table1 = []
            summary1 = cdb1.get_family_task_summary(
                dash_dict[suite1]['family_list'][0])
            # add header row
            table1 += [['Task Family'] + summary1.keys()]

            for fam1 in dash_dict[suite1]['family_list']:
                summary1 = cdb1.get_family_task_summary(fam1)
                table1 += [[fam1] + summary1.values()]
            html_output1 += create_html_table(table1)
            print(html_output1)
        except:
            # no exception type specified as whatever the error,
            # I want the dashboard to report an error for that suite and
            # continue looking at the other suites.
            print('<br><b><font color=red>ERROR: test suite output '
                  'not found or corrupt.</font></b><br>')


if __name__ == '__main__':
    main()

