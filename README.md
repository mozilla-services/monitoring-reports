# Monitoring Reports

This repo is for storing code related to generating reports based on our
monitoring data. Currently it just contains one script related to incident
reporting, ut it may expand to scripts for tracking SLOs and other purposes in
the future,

## Incidents

incident_reports.py pulls data from the Pagerduty API, creates a JSON file, and
uploads it to S3.

The script is meant to be run daily as a Lambda function. Running `build.sh`
will produce lambda.zip, which is ready to deploy to Lambda.

You must set `PAGERDUTY_API_KEY` and `S3_BUCKET` in the enviroment before
running this script.  Other settings exist and are documented in settings.py

The output is suitable for querying via Athena. A script for setting up Athena,
`setup_athena.py` is provided which takes one argument, which should be the value
you used for `S3_BUCKET`.
