#!/usr/bin/env python

import boto3
import sys

bucket = sys.argv[1]
prefix = 'slo'

db_query = 'CREATE DATABASE IF NOT EXISTS monitoring_reports;'

# Note the double escaping on the slashes
table_query = """CREATE EXTERNAL TABLE IF NOT EXISTS monitoring_reports.%s (
  `date` timestamp,
  `component` string,
  `uptime` float,
  `num_outages` int
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
LOCATION 's3://%s/%s/'
TBLPROPERTIES ('has_encrypted_data'='false');
""" % (prefix, bucket, prefix)

result_configuration = {'OutputLocation': 's3://%s/setup/' % bucket}

print('Creating athena table monitoring_reports.%s at s3://%s/%s with' %
      (prefix, bucket, prefix))
print(table_query)

client = boto3.client('athena')
client.start_query_execution(QueryString=db_query,
                             ResultConfiguration=result_configuration)
client.start_query_execution(QueryString=table_query,
                             ResultConfiguration=result_configuration)