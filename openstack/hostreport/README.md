This directory contains a poython script to parse drop log files and provide
summarized or limited output. 

# Usage

Run the tool to see the available commands
<pre><code>$ python3 report_parser.py
Usage: report_parser.py [OPTIONS] COMMAND [ARGS]...

  Commands for Opflex droplog collection and introspection

Options:
  --help  Show this message and exit.

Commands:
  show
  summarize
</code></pre>

Each command has options:
<pre><code>$ python3 report_parser.py show --help
Usage: report_parser.py show [OPTIONS]

Options:
  --droplog-file TEXT  Drop log file name  [required]
  --start-time TEXT    Only consider entries starting after this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds.
  --stop-time TEXT     Only consider entries starting before this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds.
  --table TEXT         Only consider drops from these tables
  --help               Show this message and exit.
</code></pre>
<pre><code>$ python3 report_parser.py summarize --help
Usage: report_parser.py summarize [OPTIONS]

Options:
  --droplog-file TEXT  Drop log file name  [required]
  --start-time TEXT    Only consider entries starting after this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds.
  --stop-time TEXT     Only consider entries starting before this time. Format
                       is yyyy-mmm-dd hh:mm:ss.uuuuuu, where yyyy is year, mmm
                       is the first 3 letters of the month, dd is the day, hh
                       is the hour, mm is the minute, ss are the seconds, and
                       uuuuuu are the subseconds.
  --interval TEXT      Summarize entries over interval (seconds, minutes,
                       hours)
  --exclude TEXT       Exclude these fields when making comparisons
  --help               Show this message and exit.
</code></pre>

# Sample commands
1. Show the logs from a particular interval, and only from a specific table

<pre><code>$  python3 report_parser.py show --start-time '2024-Mar-06 16:11:00.000000' --stop-time '2024-Mar-06 16:11:10.000000' --droplog-file /some/directory/opflex-droplog.log --table=Int-PORT_SECURITY_TABLE
</code></pre>

2. Summarize logs for each second, over a given period of time, and wildcard/exclude SEQA, TTL, DSCP, FLAGS, ACK, and WINDOWS fields when matching:

<pre><code>$ python3 report_parser.py summarize --start-time '2024-Mar-06 16:11:00.000000' --stop-time '2024-Mar-06 16:11:10.000000' --droplog-file /some/directory/opflex-droplog.log --exclude ID --exclude SEQ --exclude TTL --exclude DSCP --exclude FLAGS --exclude ACK --exclude WINDOWS --interval seconds
</code></pre>

