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

import click

import report_db

DEFAULT_TABLES=[
        'Int-SOURCE_TABLE', 
        'Acc-SEC_GROUP_IN_TABLE',
        'Acc-SEC_GROUP_OUT_TABLE',
        'Acc-GROUP_MAP_TABLE',
        'Int-PORT_SECURITY_TABLE',
        'Int-SERVICE_REV_TABLE',
        'Int-BRIDGE_TABLE',
        'Int-POL_TABLE']

DEFAULT_EXCLUDES=['ID', 'SEQ', 'TTL', 'DSCP', 'FLAGS', 'ACK', 'WINDOWS', 'URGP']


@click.group()
def report_parser():
    """Commands for Opflex droplog collection and introspection"""
    pass

@report_parser.command(name="summarize")
@click.option('--droplog-file', required=True,
              help='Drop log file name')
@click.option('--start-time', required=False, default=None,
              help=("""Only consider entries starting after this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds."""))
@click.option('--stop-time', required=False, default=None,
              help=("""Only consider entries starting before this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds."""))
@click.option('--interval', required=False, default=None,
              help='Summarize entries over interval (seconds, minutes, hours)')
@click.option('--exclude', required=False, default='', multiple=True,
              help='Exclude these fields when making comparisons')
def summarize(droplog_file, start_time=None, stop_time=None, interval=None, exclude=DEFAULT_EXCLUDES):
    droplog_db = report_db.DropLogDbManager(droplog_file)
    droplog_db.summarize_drops(start_time=start_time, stop_time=stop_time,
                               interval=interval, exclude=exclude)

@report_parser.command(name="show")
@click.option('--droplog-file', required=True,
              help='Drop log file name')
@click.option('--start-time', required=False, default=None,
              help=("""Only consider entries starting after this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds."""))
@click.option('--stop-time', required=False, default=None,
              help=("""Only consider entries starting before this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds."""))
@click.option('--table', required=False, default='', multiple=True,
              help='Only consider drops from these tables')
def show(droplog_file, start_time=None, stop_time=None, table=DEFAULT_TABLES):
    droplog_db = report_db.DropLogDbManager(droplog_file)
    droplog_db.show_drops(start_time=start_time, stop_time=stop_time,
                          table=table)


def run():
    report_parser(auto_envvar_prefix='REPORTPARSER')


if __name__ == '__main__':
    run()
