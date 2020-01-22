import os
from datetime import datetime, timedelta, timezone

# credential for pingdom v3 api
API_KEY = os.environ['API_KEY']
# s3 url to upload report into
S3_BUCKET = os.environ['S3_BUCKET']
S3_PREFIX = 'pingdom_outages/'

# Fetch everything from yesterday to now
START_DATE = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) - timedelta(days=1)
END_DATE = datetime.now(timezone.utc)

OUTPUT_PATH = "/tmp/pingdom_report/"
