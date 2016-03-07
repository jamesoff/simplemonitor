-- sqlite3 schema for monitor.db

CREATE TABLE results(
result_id integer primary key,
monitor_host varchar(50),
monitor_name varchar(50),
monitor_type varchar(50),
monitor_params varchar(100),
monitor_result int,
timestamp int,
monitor_info varchar(255));

CREATE TABLE status (
monitor_host varchar(50),
monitor_name varchar(50),
monitor_result int,
monitor_info varchar(255));

