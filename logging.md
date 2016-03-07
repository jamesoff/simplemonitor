---
layout: page
title: Logging
order: 30
---

Loggers are used by SimpleMonitor to record the state of all monitors after each interval.

The types of loggers are:

* db: Records the result of every monitor, every iteration (maintaining a history) in a SQLite database.
* dbstatus: Records a snapshot of the current state of every monitor in a SQLite database.
* logfile: Records a logfile of the result of every monitor, or only the monitors which failed. Each line is preceeded by the current UNIX timestamp.
* html: Writes an HTML file showing the status of all monitors (including remote ones).
* network: Sends status of all monitors to a remote host.

## Defining a logger

The section name should be the name of your logger. This is the name you should give in the "loggers" setting in the "reporting" section of the configuration. All loggers take these two parameters.

| setting | description | required | default |
|---|---|---|---|
|type|the type of logger to create. Choose one of the five in the list above.|yes| |
|depend|lists (comma-separated, no spaces) the names of the monitors this logger depends on. Use this if the database file lives over the network. If a monitor it depends on fails, no attempt will be made to update the database.| no | |

### db and dbstatus loggers

| setting | description | required | default |
|---|---|---|---|
|path|the path/filename of the SQLite database file. You should initialise the schema of this file using the monitor.sql file in the distribution. You can use the same database file for many loggers.| yes | |

### logfile loggers

| setting | description | required | default |
|---|---|---|---|
|filename|the filename to write to. Rotating this file underneath SimpleMonitor will likely result in breakage (this will be addressed later).|yes| |
|buffered|set to 1 if you aren’t going to watch the logfile in real time. If you want to watch it with something like tail -f then set this to 0.|no|0|
|only_failures|set to 1 if you only want failures to be written to the file.|no|0|

### html loggers

| setting | description | required | default |
|---|---|---|---|
|folder|the folder in which all the needed files live. This is probably going to be html if you don’t move things around from the default distribution.|yes | |
|filename|the filename to write out. The file will be updated once per interval (as defined in the main configuration). Relative to the *folder*. If you don’t write the output file to the same folder as folder above, you will need to copy/move styles.css to the same place.|yes| |
|header|the header include file which is sucked in when writing the output file. Relative to folder.|yes| |
|footer|the footer include file. Relative to folder.|yes| |

The header and footer files do not necessarily need to be in the publicly accessibly folder that the output is written to, but no harm will come if they are.

The supplied header file includes JavaScript to notify you if the page either doesn’t auto-refresh, or if SimpleMonitor has stopped updating it. This requires your machine running SimpleMonitor and the machine you are browsing from to agree on what the time is (timezone doesn’t matter)!

### network logger
This logger is used to send status reports of all monitors to a remote instance. The remote instance must be configured to listen for connections. The *key* parameter is a shared secret used to generate a hash of the network traffic so the receiving instance knows to trust the data. (Note that the traffic is not encrypted, just given a hash.)

| setting | description | required | default |
|---|---|---|---|
|host|the remote host to send to.|yes| |
|port|the port on the remote host to connect to.|yes| |
|key|shared secret to protect communications|yes| |

