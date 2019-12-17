#!/usr/bin/env python3

from datetime import datetime, timedelta
from pytz import timezone
import boto3
import json
import requests
import settings
import collections


def timerange_for_report():
    start_date = settings.START_DATE
    end_date = settings.END_DATE
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def statuspage_request(path, offset=1):
    url = "http://api.statuspage.io/v1/pages/%s/%s/?page=%s" % (
        settings.PAGE_ID,
        path,
        offset,
    )
    headers = {"Authorization": "OAuth %s" % settings.API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_components():
    components = []
    offset = 1
    r = statuspage_request('components.json', offset)
    components = components + r
    while len(r) == 100:
        offset += 1
        r = statuspage_request("components.json", offset)
        components = components + r
    return components


def check_if_need_more_incidents(incidents):
    if len(incidents) != 100:
        return False

    earliest_resolved = read_statuspage_timestamp(
        incidents[-1]['resolved_at']).date()
    if earliest_resolved < settings.START_DATE:
        return False

    return True


def get_incidents():
    incidents = []
    offset = 1
    r = statuspage_request("incidents.json", offset)
    incidents = incidents + r
    while check_if_need_more_incidents(r):
        offset += 1
        r = statuspage_request("incidents.json", offset)
        incidents = incidents + r
    return incidents


def incident_is_ongoing(i):
    return i['status'] != 'resolved'


def read_statuspage_timestamp(timestamp):
    dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    return timezone('UTC').localize(dt)


# JSON SerDE wants timestamp to be yyyy-mm-dd hh:mm:ss[.fffffffff]
def timestamp_for_hive(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_incident_duration(i):
    created = read_statuspage_timestamp(i['created_at'])
    resolved = read_statuspage_timestamp(i['resolved_at'])
    delta = resolved - created
    return int(delta.total_seconds())


def find_groups(components):
    groups_by_id = {}
    for c in components:
        if c["group"]:
            groups_by_id[c["id"]] = c["name"]
    return groups_by_id


def group_incidents_by_day(incidents):
    incidents_by_day = collections.defaultdict(list)
    for i in incidents:
        # skip ongoing incidents
        if i['resolved_at'] is None:
            continue
        # skip incidents flagged as false positive in their postmortem
        if i['postmortem_body'] and 'false positive' in i[
                'postmortem_body'].lower():
            continue
        # skip incidents with no component
        if len(i["components"]) < 1:
            continue
        # skip incidents that aren't for a day we are configured to report on
        resolved_day = read_statuspage_timestamp(i['resolved_at']).date()
        if resolved_day < settings.START_DATE or resolved_day > settings.END_DATE:
            continue
        # passed all our tests so include in list
        incidents_by_day[resolved_day].append(i)
    return incidents_by_day


def find_downtimes_by_component(components, incidents):
    downtimes_by_component = {c['name']: [] for c in components}
    for i in incidents:
        duration = calculate_incident_duration(i)
        for c in i['components']:
            downtimes_by_component[c['name']].append(duration)
    return downtimes_by_component


def generate_slo_report(downtimes_by_component, day):
    rows = []
    day = timestamp_for_hive(day)
    for name, downtimes in downtimes_by_component.items():
        total_downtime = sum(downtimes)
        downtime_percentage = (total_downtime / (24 * 60 * 60)) * 100
        uptime_percentage = 100 - downtime_percentage
        num_outages = len(downtimes)
        rows.append({
            'date': day,
            'component': name,
            'uptime': uptime_percentage,
            'num_outages': num_outages
        })
    return rows


def generate_incident_report(incidents, groups_by_id, day):
    rows = []
    for i in incidents:
        # get all updates sorted oldest to newest
        updates = "\t".join([u["body"] for u in i["incident_updates"][::-1]])
        updates += f'\t{i["postmortem_body"]}'

        # some incidents may have affect multiple components
        # create duplicate records per component in that case
        for component in i["components"]:
            row = {
                "name":
                i["name"],
                "id":
                i["id"],
                "created_at":
                timestamp_for_hive(read_statuspage_timestamp(i["created_at"])),
                "resolved_at":
                timestamp_for_hive(read_statuspage_timestamp(
                    i["resolved_at"])),
                "duration":
                calculate_incident_duration(i),
                "component_name":
                component["name"],
                "component_id":
                component["id"],
                "group":
                groups_by_id[component["group_id"]],
                "impact":
                i["impact"],
                "description":
                updates,
            }
            rows.append(row)
    return rows


def write_report(rows, output_path):
    with open(output_path, 'w') as f:
        for row in rows:
            # JSON SerDe wants one object per line
            f.write("%s\n" % json.dumps(row))


def upload_report(output_path, prefix, display_day):
    s3_name = "%s/%s.json" % (prefix, display_day)
    if settings.DRY_RUN:
        print("would upload %s to %s" % (output_path, s3_name))
    else:
        s3 = boto3.client('s3')
        s3.upload_file(output_path, settings.S3_BUCKET, s3_name)


def lambda_handler(event, context):
    components = get_components()
    groups_by_id = find_groups(components)
    incidents = get_incidents()
    incidents_by_day = group_incidents_by_day(incidents)

    for day in timerange_for_report():
        display_day = day.strftime('%Y-%m-%d')
        print('processing %s' % display_day)

        downtimes_by_component = find_downtimes_by_component(
            components, incidents_by_day[day])
        rows = generate_slo_report(downtimes_by_component, day)
        output_path = '/tmp/slo_%s.json' % display_day
        write_report(rows, output_path)
        upload_report(output_path, 'slo', display_day)

        rows = generate_incident_report(incidents_by_day[day], groups_by_id,
                                        day)
        output_path = '/tmp/incident_%s.json' % display_day
        if rows:
            write_report(rows, output_path)
            upload_report(output_path, 'statuspage_incidents', display_day)


if __name__ == '__main__':
    lambda_handler(None, None)
