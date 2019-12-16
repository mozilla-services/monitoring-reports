import os
from datetime import datetime, timedelta, timezone

# credential for pingdom v3 api
API_KEY = os.environ['API_KEY']
# s3 url to upload report into
S3_BUCKET = os.environ['S3_BUCKET']
S3_PREFIX = 'pingdom/'
# regen previous week on every run
# to account for people filling in postmortems
# end is exclusive so skips current day
START_DATE = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) - timedelta(days=8)

OUTPUT_PATH = "/tmp/pingdom_report/"
