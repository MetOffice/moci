#!/usr/bin/python3
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

    Installation notes: the script must use a full path to python3 and
    not /usr/bin/env.  The script does not currently work with
    timezones enable.
"""

import sys
import os
import re
import sqlite3
import configparser
from functools import reduce
import logging

import datetime
import time
import socket
from errno import EAGAIN, EACCES
from fcntl import flock, LOCK_EX, LOCK_NB, LOCK_UN


# Cache settings
owner = os.stat(sys.argv[0]).st_uid
cache_name = f"test_suite_dashboard_{owner}"
cache_durations = {
    "get_tasks_in_family": 43200,  # Cache family information for 12 hours
    "get_family_task_status": 60,  # Cache status details for a minute
}


DT_STR_TEMPLATE = \
    '{dt.year}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}'


logging.basicConfig(level=logging.DEBUG)


class Locker:

    """File lock context manager.

    Make repeated attempts to lock a file using the operating system
    fcntl flock call.  If the timeout expires before the lock is obtained,
    an EGAIN exception is raised.

    The class is intended to be used in a with block, with enter
    locking the file and exit releasing it.

    :param fd: a valid file descriptor
    :param timeout: time to wait for a lock
    :type float, optional
    :param interval: lock retry interval
    :type float, optional
    """

    def __init__(self, fd, timeout=5.0, interval=0.2):

        self.fd = fd
        self.timeout = float(timeout)
        self.interval = float(interval)
        self.locked = False

    def __enter__(self):

        self.locked = False
        t0 = time.time()

        while (time.time() - t0) < self.timeout:
            # While the timer is below the timeout threshold

            try:
                # Attempt to lock the file and stop looping if successful
                flock(self.fd,  LOCK_EX | LOCK_NB)
                self.locked = True
                break

            except OSError as error:
                # EAGAIN and EACCES indicate waiting for a lock but
                # anything else is a genuine error
                if error.errno not in (EAGAIN, EACCES):
                    raise

            time.sleep(self.interval)

        if not self.locked:
            # Raise an exception if locking has timed out
            raise OSError(EAGAIN,
                          os.strerror(EAGAIN),
                          self.fd.name)

        return self

    def __exit__(self, *args):

        if self.locked:
            # If the file is locked, release it
            flock(self.fd, LOCK_UN)
            self.locked = False


class SqlDatabase:
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
        if hasattr(self, "db_cursor") and self.db_cursor:
            self.db_cursor.close()
        if hasattr(self, "db_connection") and self.db_connection:
            self.db_connection.close()

    def select_from_table(self, table_name, columns,
                          limit=None, reverse=False):
        """
        Select items from the table of the database.
        :param table_name: The name of the table to select from.
        :param columns: The name of columns to select
        :param limit: Limit number of SQL rows to return
        :type int, optional
        :param reverse: Reverse the table order
        :type bool, optional
        :return: The items from the select call.
        """
        columns_str = ','.join(columns)
        db_cmd1 = 'SELECT {columns} FROM {table_name}'

        # Optimisations to speed up some date operations
        if reverse:
            # Use sqlite to reverse the table
            db_cmd1 += " ORDER BY rowid DESC"
        if limit:
            # Limit to a subset of rows in the database
            db_cmd1 += f" LIMIT {int(limit)}"
        db_cmd1 += ";"

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

    HIGHLIGHT_COLOURS = {
        STATUS_SUCCEEDED: '#FFFFFF',   # No highlight
        STATUS_WAITING: '#FF7700',     # highlight orange
        STATUS_FAILED: '#FF0000',      # highlight red
        STATUS_RUNNING: '#00FF00',     # highlight green
        STATUS_OTHER: '#FFFF00',       # highlight yellow
        'SummaryBar': '#DDDEE5',       # Highlight grey
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
        self.suite_title = title
        if suite_name.startswith(title):
            self.title = suite_name
        else:
            self.title = title
        self.description = description
        self.suite_run_dir = cylc_run_path
        self.rose_bush_url = rose_bush_url
        path_db = os.path.join(self.suite_run_dir,
                               CylcDB.CYLC_DB_FNAME)

        if not os.path.exists(path_db):
            # If database does not exist, try a cylc 8 path instead
            path_db = os.path.join(self.suite_run_dir,
                                   "runN", "log", "db")
            self.rose_bush_url += "%2FrunN"

        self.test_categories = test_categories
        self.family_list = family_list
        try:
            test_freq_hrs = re.match(r'^(\d*)[dD]', test_frequency).group(1)
            test_freq_hrs = int(test_freq_hrs) * 24
        except AttributeError:
            test_freq_hrs = re.match(r'^(\d*)[hH]?', test_frequency).group(1)
        self.test_freq_hrs = int(test_freq_hrs)

        SqlDatabase.__init__(self, path_db)
        self.db_mtime = os.stat(path_db).st_mtime

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

    def cache_db(func):

        """Decorator to cache database queries.

        The sqlite3 calls and data transforms are expensive.  Try to
        save the output to a temporary file to speed things along.
        """

        path = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                            cache_name, func.__name__)

        if not os.path.exists(path):
            os.makedirs(path)

        # Use a specific time for the function if one has been defined
        # or fall back on a default of 60 seconds
        ttl = cache_durations.get(func.__name__, 60)
        logging.info("using cache %r with age of %ss",
                     path, ttl)

        def inner(self, *args, **kwargs):
            name = os.path.join(path, self.suite_title) + "." + args[0]

            result = []

            if os.path.exists(name):

                mtime = os.stat(name).st_mtime
                age = time.time() - mtime
                if mtime >= self.db_mtime or age <= ttl:
                    # Cache is still valid

                    with open(name, encoding="utf-8") as fd:
                        for line in fd:
                            items = line.strip().split()
                            if len(items) == 1:
                                items = items[0]
                            result.append(items)

                    return result

            # Use live data and rebuild the cache.  Lock the file to
            # prevent problems with concurrent accesses on the same
            # webserver
            with open(name, "w", encoding="utf-8") as fd:
                with Locker(fd):
                    for item in func(self, *args, **kwargs):
                        result.append(item)
                        if isinstance(item, str):
                            value = item
                        elif isinstance(item, (tuple, list)):
                            value = " ".join(item)
                        fd.write(value + "\n")

            return result

        return inner

    @cache_db
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

    @cache_db
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

        # Python 3 preserves key ordering, so this definition defines
        # the appears of the output table
        summary1 = {
            CylcDB.STATUS_FAILED: 0,
            CylcDB.STATUS_RUNNING: 0,
            CylcDB.STATUS_OTHER: 0,
            CylcDB.STATUS_WAITING: 0,
            CylcDB.STATUS_SUCCEEDED: 0,
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
                html_output1 += f'{fam1}: '
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
                logging.info('%s - %s', fam1, stat_txt)
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
                link1 += f'&task_status={status}'

            cell_html = row_fmt.format(
                col=CylcDB.HIGHLIGHT_COLOURS['SummaryBar'],
                name=f'<a href={link1}>{cat1} </a>'
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

            for cat1, value in summary1.items():
                shade = cell_col
                if value > 0 and cat1 != CylcDB.STATUS_SUCCEEDED:
                    shade = cat1
                row_html += row_fmt.format(
                    col=CylcDB.HIGHLIGHT_COLOURS[shade],
                    name=value,
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
        logging.info('producing output for %s', self.title)
        html_output1 = ''
        html_output1 += '<div class="row">\n'
        html_output1 += f'<h2>{self.title}</h2><br>\n'

        html_output1 += '</div><div class="row">\n'

        html_output1 += '    <div class="column">\n'
        try:
            html_output1 += f'<p>{self.description}<br>\n'
        except KeyError:
            html_output1 += '<p>\n'
        html_output1 += f'\n<a href={self.rose_bush_url}>'
        html_output1 += 'Rose bush output</a><br>\n'
        start_dt_str = \
            DT_STR_TEMPLATE.format(dt=self.get_suite_start_time())
        html_output1 += f'suite started at {start_dt_str}<br>\n'
        lastsubmit_dt_str = \
            DT_STR_TEMPLATE.format(dt=self.get_suite_lastsubmit_time())
        html_output1 += 'suite last submitted a task at '
        html_output1 += f'{lastsubmit_dt_str}<br>\n'
        if not self.suite_date_valid(lastsubmit_dt_str):
            html_output1 += '<b><font color="red"> Warning </font>'
            html_output1 += 'This suite has not submitted a task in the past '
            html_output1 += str(self.test_freq_hrs)
            html_output1 += ' hours. Please investigate</b><br>\n'
        html_output1 += self.create_summary_list(self.test_categories)
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
        # Assume that start is the first entry
        dt_list = self.select_from_table('task_events', ['time'], 1)
        dt_list = [self._parse_date(dt1[0]) for dt1 in dt_list]
        start_datetime = min(dt_list)
        return start_datetime

    def get_suite_lastsubmit_time(self):
        """
        Get the time of the last task submission for a suite.
        :return: A python datetime object with the submission time of the
                 first task submitted.
        """
        # Assume that last submit is the last entry
        dt_list = self.select_from_table('task_events', ['time'], 1, True)
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
                                 int(value[14:16]), int(value[17:19]))


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
            html_output1 += f'<td> {column1} </td>'
        html_output1 += '</tr> \n'
    html_output1 += '</table>\n'
    return html_output1


def print_html_header(logo_file, wiki_url):
    """
    Create a standard hml header.
    :return: A string containing a standard html header.
    """
    dt_str = DT_STR_TEMPLATE.format(dt=datetime.datetime.now())
    time_gen_str = f'<p>Dashboard generated at {dt_str}</p><br>'

    print('Content-Type: text/html;charset=utf-8\n')
    print(f'''<html>\n \
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<head>
    <title> Test Suite Dashboard</title>
    <link rel="stylesheet" type="text/css" href="dashboard.css">
</head>
<body>

<div class="row">
    <div class="header_logo_cell">
        <a href="http://www.metoffice.gov.uk" target="_blank"
           title="opens in a new window">
           <img
            src="http://www.metoffice.gov.uk/lib/template/logos/MO_Master_W.jpg"
            alt="Met Office" title="www.metoffice.gov.uk"
            width="120" height="109" /></a>
    </div>
    <div class="header_text_cell">
        <h1> Test Suite Dashboard</h1>
        {time_gen_str}
    </div>
    <div class="header_logo_cell">
         <a href="{wiki_url}"><img src="{logo_file}"
            title="LOGO" width="350"/></a>
    </div>
</div>
''')


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
                test_dict1['cylc_run_path'] = os.path.join(cylc_run_path,
                                                           test1)
                test_dict1['rose_bush_url'] = rose_bush_base_url + test1

                dash_dict[test1] = test_dict1
                test_avail = True
        if not test_avail:
            # No test available in cylc_runs - add incomplete dict to
            # flag the loss This will raise a TypeError on
            # instantiation of the CylcDB object
            dash_dict[suite1] = test_dict1

    return dash_dict, logo_file, wiki_url


def main():
    """
    The main function for this module.
    """

    logging.info("started")
    tstart = datetime.datetime.now()

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

        except TypeError:
            # Incomplete dict as no cylc-runs directory found
            freq = dash_dict[suite1]['test_frequency']
            if freq in ['24h', '1d']:
                period = 'DAILY '
            elif freq in ['7d', '1w']:
                period = 'WEEKLY '
            else:
                period = ''
            print(f'<br><b><font color=blue>Output is absent for {period}'
                  f'test suite: {suite1}.</font></b><br>')
            print('</div>\n')

        except Exception as error:
            # Catch all exceptions as whatever the error
            # I want the dashboard to report an error for that suite and
            # continue looking at the other suites.
            logging.exception("error encountered in %s", suite1)
            print('<br><b><font color=red>ERROR: Output for '
                  f'requested test suite: {suite1} '
                  'appears to be corrupt.</font></b><br>')

            print(f"<P>The error was as follows:</p><pre>\n{error}\n</pre>")

            print('</div>\n')

    for _, suite_html1 in reversed(sorted(html_output.items())):
        print(suite_html1)
        print('</div>\n')

    tend = datetime.datetime.now()

    # Add a comment containing some diagnostics
    print(f"<!--\nTime taken: {tend - tstart}\n"
          f"Python: {sys.version_info.major}.{sys.version_info.minor}"
          f".{sys.version_info.micro}\n"
          f"Host: {socket.gethostname()}\n-->\n")

    print("</body>\n</html>")

    logging.info("completed in %ss", tend - tstart)


if __name__ == '__main__':
    main()
