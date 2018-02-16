import os
from datetime import date

# credential for pagerduty v2 api
PAGERDUTY_API_KEY = os.environ['PAGERDUTY_API_KEY']
# s3 url to upload report into
S3_BUCKET = os.environ['S3_BUCKET']
S3_PREFIX = 'incidents/'
# when to anchor report and how far back to run it
END_DATE = date.today()
DAYS_BACK = 1
# start and end of day in local time zone for determining out of hours
START_OF_DAY = 9
END_OF_DAY = 17
# if any of these are a susbtring of the service name, exclude it
SERVICE_NAMES_TO_EXCLUDE = ['Out of hours']
# set to true to only report on high urgency incidents
EXCLUDE_LOW_URGENCY = True
