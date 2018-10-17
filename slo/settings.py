import os
from datetime import date

# credential for statuspage v1 api
API_KEY = os.environ['API_KEY']
# id of our status page
PAGE_ID = '76k9j8n4y3zt'
# s3 url to upload report into
S3_BUCKET = os.environ['S3_BUCKET']
S3_PREFIX = 'slo/'
# day to report on
DATE_FOR_REPORT = date.today()