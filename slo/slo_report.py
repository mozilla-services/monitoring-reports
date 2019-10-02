#!/usr/bin/env python3

from datetime import datetime, timedelta
from os import path
from pytz import timezone
import boto3
import json
import requests
import settings

def timerange_for_report():
    start_date = settings.START_DATE
    end_date = settings.END_DATE
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


def statuspage_request(path):
    url = 'http://api.statuspage.io/v1/pages/%s/%s' % (settings.PAGE_ID, path)
    headers = {'Authorization': 'OAuth %s' % settings.API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_components():
    return statuspage_request('components.json')


def get_incidents():
        return statuspage_request('incidents.json')


def incident_is_ongoing(i):
    return i['status'] != 'resolved'


def skip_incident(i, report_day):
    # skip ongoing incidents
    if i['resolved_at'] is None:
        return True
    # skip incidents flagged as false positive in their postmortem
    if i['postmortem_body'] and 'false positive' in i['postmortem_body'].lower():
        return True
    # skip incidents that aren't for the day are configured to report on
    resolved = datetime.strptime(i['resolved_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
    resolved = timezone('UTC').localize(resolved)
    resolved_day = resolved.date()
    if resolved_day == report_day:
        return False
    else:
        return True


def calculate_incident_duration(i):
    created = datetime.strptime(i['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
    resolved = datetime.strptime(i['resolved_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
    delta = resolved - created
    return delta.total_seconds()


def find_downtimes_by_component(components, incidents, day):
    downtimes_by_component = {c['name']: [] for c in components}
    for i in incidents:
        if skip_incident(i, day):
            continue
        duration = calculate_incident_duration(i)
        for c in i['components']:
            downtimes_by_component[c['name']].append(duration)
    return downtimes_by_component


def generate_report(downtimes_by_component, day):
    rows = []
    # JSON SerDE wants timestamp to be yyyy-mm-dd hh:mm:ss[.fffffffff
    day = day.strftime('%Y-%m-%d %H:%M:%S')
    for name, downtimes in downtimes_by_component.items():
        total_downtime = sum(downtimes)
        downtime_percentage = (total_downtime / (24 * 60 * 60)) * 100
        uptime_percentage = 100 - downtime_percentage
        num_outages = len(downtimes)
        rows.append({'date': day, 'component': name, 'uptime': uptime_percentage,
                    'num_outages': num_outages})
    return rows


def write_report(rows, output_path):
    with open(output_path, 'w') as f:
        for row in rows:
            # JSON SerDe wants one object per line
            f.write("%s\n" % json.dumps(row))


def upload_report(output_path):
    s3_name = "%s%s" % (settings.S3_PREFIX, path.basename(output_path))
    s3 = boto3.client('s3')
    s3.upload_file(output_path, settings.S3_BUCKET, s3_name)


def lambda_handler(event, context):
    components = get_components()
    incidents = get_incidents()
    for day in timerange_for_report():
        output_path = '/tmp/%s.json' % (day).strftime('%Y-%m-%d')
        downtimes_by_component = find_downtimes_by_component(components, incidents, day)
        rows = generate_report(downtimes_by_component, day)
        write_report(rows, output_path)
        upload_report(output_path)


if __name__ == '__main__':
    lambda_handler(None, None)
