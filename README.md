# Monitoring Reports

This repo is for storing code related to generating reports based on our
monitoring data. Currently it just contains one script related to incident
reporting, ut it may expand to scripts for tracking SLOs and other purposes in
the future,

## Incidents

incident_reports.py pulls data from the Pagerduty API, creates a CSV file, and
uploads it to S3.

The output is suitable for querying via Athena. A working schema is


```
  `id` string,
  `title` string,
  `urgency` string,
  `escalation_policy` string,
  `service` string,
  `created_at` timestamp,
  `time_to_acknowledge` int,
  `time_to_resolve` int,
  `num_acknowledgments` int,
  `num_users_notified` int,
  `user` string,
  `out_of_hours` boolean 
```

The script is meant to be run daily as a Lambda function. Running `build.sh`
will produce lambda.zip, which is ready to deploy to Lambda.

You must set `PAGERDUTY_API_KEY` and `S3_BUCKET` in the enviroment before
running this script.  Other settings exist and are documented in settings.py
