# Copyright (c) 2019 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import json
import netaddr

FIRST_TIME=datetime.datetime(datetime.MINYEAR,1, 1)
LAST_TIME=datetime.datetime(datetime.MAXYEAR,12,31)

month_to_number = {'jan': 1, 'feb': 2, 'mar': 3,
                   'apr': 4, 'may': 5, 'jun': 6,
                   'jul': 7, 'Aug': 8, 'sep': 9,
                   'oct': 10, 'nov': 11, 'dec': 12}



class DropLogDbEntry(object):
    """Opflex Droplog message

    Opflex drop log messages have a format. We parse the message
    into its fields, and store them as a dctionary (key-value pairs),
    so they can be used for comparison.

    The DropLogDbEntry presumes that the first four fields are:
    * "[yyyy-mo-dd'" date format, where "mo" is the first three
       letters of the month.
    * "hh:mm:ss:.mmmmmm]" time formate, where mmmmmm is the sub
       second value
    * "<table name>", which is a string representation of a flow table
    * "<action>", which should always be "MISS"
    """

    def __init__(self, droplog_line):
        self.fields = []
        self.unkeyed = []
        self.kv_dict = {}
        for field_cnt, log_field in enumerate(droplog_line.split()):
            # Special case first few fields
            if field_cnt == 0:
                self.date = log_field[1:]
            elif field_cnt == 1:
                self.time = log_field[:-1]
            elif field_cnt == 2:
                self.table = log_field
            elif '=' in log_field:
                k,v = log_field.split('=')
                self.kv_dict[k] = v
            else:
                self.unkeyed.append(log_field)
            self.fields.append(log_field)

    def get_property(self, property_name):
        if log_key in self.kv_dict:
            return self.kv_dict.get(log_key)
        try:
            return self.fields.index(property_name)
        except ValueError:
            return None

    def do_print(self):
        line = ''
        for field in self.fields:
            line += field + " "
        print(line)

    def date_time(self):
        return self.date + " " +  self.time

    def __str__(self):
        line = ''
        for field in self.fields[4:]:
            line += field + " "
        return line


class DropLogSummaryInterval(object):

    def __init__(self, start_time=None, stop_time=None, interval=None):
        self.summarized = {}
        if start_time == None:
            start_time = FIRST_TIME
        if interval:
            try:
                s_time = start_time + interval
            except OverflowError:
                s_time = LAST_TIME
        else:
            s_time = LAST_TIME
        if stop_time == None:
            stop_time = s_time
        elif s_time < stop_time:
            stop_time = s_time
        self.start_time = start_time
        self.stop_time = stop_time
        self.interval = interval


class DropLogDbManager(object):
    """Droplog Database Manager

    This class provides a set of APIs to introspect drop log files.
    """
    def __init__(self, droplog_filename):
        self.filename = droplog_filename
        self.intervals = []
        self._get_droplog_entries()

    def parse_date_time(self, date_time):
        date, time = date_time.split()
        yyyy, mmm, dd = date.split('-')
        hh,mm,s = time.split(':')
        ss,mmmmmm = s.split('.')
        return datetime.datetime(int(yyyy), month_to_number[mmm.lower()],
                                 int(dd), int(hh), int(mm), int(ss),
                                 int(mmmmmm))

    def _get_droplog_entries(self):
        with open(self.filename, 'r') as fd:
            self.all_droplog_lines = fd.readlines()

    def show_drops(self, start_time=None, stop_time=None, table=None):
        """Provide summary of all drops seen in the logs.

        Look for any entries that are the same, and summarize
        them with their matching properties and total count.

        """
        self._show_drops(start_time=start_time,
                         stop_time=stop_time, table=table)

    def summarize_drops(self, start_time=None, stop_time=None, interval=None, exclude=None):
        """Provide summary of all drops seen in the logs.

        Look for any entries that are the same, and summarize
        them with their matching properties and total count.

        For intervals, we expect the entries in the file to
        be ordered by date and time.
        """
        self._summarize_drops(start_time=start_time, stop_time=stop_time,
                              interval=interval, exclude=exclude)

    def _show_drops(self, exclude=None, start_time=None,
                    stop_time=None, table=None):
        if stop_time:
            stop = self.parse_date_time(stop_time)
        else:
            stop = LAST_TIME
        if start_time:
            start = self.parse_date_time(start_time)
        else:
            start = FIRST_TIME
        for droplog_line in self.all_droplog_lines:
            entry = DropLogDbEntry(droplog_line)
            curr = self.parse_date_time(entry.date_time())
            if start_time and curr < start:
                continue
            if stop_time and curr > stop:
                break
            if entry.table not in table:
                continue
            entry.do_print()

    def _summarize_drops(self, start_time=None, stop_time=None,
                         interval=None, exclude=None):
        delta = LAST_TIME - FIRST_TIME
        if stop_time:
            stop = self.parse_date_time(stop_time)
        else:
            stop = LAST_TIME
        if start_time:
            start = self.parse_date_time(start_time)
        else:
            start = FIRST_TIME
        if interval == 'seconds':
            delta = datetime.timedelta(seconds=1)
        elif interval == 'minutes':
            delta = datetime.timedelta(minutes=1)
        elif interval == 'hours':
            delta = datetime.timedelta(hours=1)
        curr_interval = DropLogSummaryInterval(start_time=start,
                                               stop_time=stop,
                                               interval=delta)
        self.intervals.append(curr_interval)
        for droplog_line in self.all_droplog_lines:
            entry = DropLogDbEntry(droplog_line)
            entry_time = self.parse_date_time(entry.date_time())
            if entry_time > curr_interval.stop_time:
                curr_interval = DropLogSummaryInterval(
                        start_time=curr_interval.stop_time,
                        stop_time=stop,
                        interval=delta)
                self.intervals.append(curr_interval)
            if entry_time < start:
                continue
            if entry_time > stop:
                break
            log_key = ''
            for key in list(entry.kv_dict.keys()):
                if key not in exclude:
                    log_key += key+entry.kv_dict[key]
            curr_interval.summarized.setdefault(log_key, []).append(entry)
        for interval in self.intervals:
            print("Start Time: %s" % interval.start_time)
            for key in list(interval.summarized.keys()):
                print("%(count)s:  %(flow)s" % {
                    'count': len(interval.summarized[key]),
                    'flow': interval.summarized[key][0]})
