import os
from datetime import date, timedelta

# DRY_RUN to skip uploading to S3
DRY_RUN = False
# credential for statuspage v1 api
API_KEY = os.environ['API_KEY']
# id of our status page
PAGE_ID = '76k9j8n4y3zt'
# s3 url to upload report into
S3_BUCKET = os.environ['S3_BUCKET']
# regen previous week on every run
# to account for people filling in postmortems
# end is exclusive so skips current day
START_DATE = date.today() - timedelta(days=8)
END_DATE = date.today()
