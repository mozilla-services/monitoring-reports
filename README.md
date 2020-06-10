# Monitoring Reports

This repo is for storing code related to generating reports based on our
monitoring data.

More documentation is available at https://mana.mozilla.org/wiki/display/SVCOPS/Monitoring+Reports

## Incidents

incident_report.py pulls data from the Pagerduty API, creates a JSON file, and
uploads it to S3.

The script is meant to be run daily as a Lambda function. Running `build.sh incident`
will produce incident_lambda.zip, which is ready to deploy to Lambda.

You must set `API_KEY` and `S3_BUCKET` in the enviroment before
running this script.  Other settings exist and are documented in settings.py

The output is suitable for querying via Athena. A script for setting up Athena,
`setup_athena.py` is provided which takes one argument, which should be the value
you used for `S3_BUCKET`.

## SLO

** Notice: We have stopped using StatusPage and thus this report is no longer run **

slo_report.py pulls data from the Statuspage API, creates a JSON file, and
uploads it to S3.

The script is meant to be run daily as a Lambda function. Running `build.sh slo`
will produce slo_lambda.zip, which is ready to deploy to Lambda.

You must set `API_KEY` and `S3_BUCKET` in the enviroment before
running this script.  Other settings exist and are documented in settings.py

The output is suitable for querying via Athena. A script for setting up Athena,
`setup_athena.py` is provided which takes one argument, which should be the value
you used for `S3_BUCKET`.
