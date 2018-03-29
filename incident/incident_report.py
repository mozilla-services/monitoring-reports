#!/usr/bin/env python3
# coding: utf-8

import settings

from datetime import datetime, timedelta
from functools import lru_cache
from os import path
from pytz import timezone
import boto3
import json
import pypd

def timerange_for_report():
    days = settings.DAYS_BACK
    today = settings.END_DATE
    start_day = today - timedelta(days=days)
    until = today.strftime('%Y-%m-%d')
    since = start_day.strftime('%Y-%m-%d')
    return (since, until)


def get_incidents(since, until):
    incidents = pypd.Incident.find(since=since, until=until, time_zone='UTC')
    return incidents


@lru_cache(maxsize=1)
def get_log_entries(incident):
    log_entries = incident.log_entries(is_overview=False)
    return log_entries


@lru_cache(maxsize=1)
def get_users_timezones():
    users = pypd.User.find()
    timezone_by_user = {user['name']: timezone(user['time_zone']) for user in users}
    return timezone_by_user


def pagerduty_datetime(time_string):
    naive_time = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%SZ')
    utc_time = timezone('UTC').localize(naive_time)
    return utc_time


def first_timestamp_for_type(all_entries, entry_type):
    relevant_entries = [log['created_at'] for log in all_entries if log['type'] == entry_type]
    if not relevant_entries:
        return None
    # list is ordered from most to least recent, so the first entry chronologically is at the end
    first_entry = relevant_entries[-1]
    timestamp = pagerduty_datetime(first_entry)
    return timestamp


def seconds_since_occurred(beginning, end):
    if not end:
        return None
    offset = end - beginning
    seconds = round(offset.total_seconds())
    return seconds


def timezone_for_user(user_name):
    timezone_by_user = get_users_timezones()
    return timezone_by_user[user_name]


def incident_was_out_of_hours(user, incident):
    user_timezone = timezone_for_user(user)
    incident_utc_time = pagerduty_datetime(incident['created_at'])
    incident_local_time = incident_utc_time.astimezone(user_timezone)
    # if during the weekend
    if incident_local_time.weekday() > 4:
        return True
    # or outside business hours
    if incident_local_time.hour < settings.START_OF_DAY or incident_local_time.hour >= settings.END_OF_DAY:
        return True
    return False


def user_credited_for_incident(users_acked, users_notified):
    # if incident was acked, credit to first user who acked it
    if users_acked:
        return users_acked[-1]
    # if not acked, credit to first user who was notified
    return users_notified[-1]


def service_is_excluded(incident):
    service_name = incident['service']['summary']
    for pattern in settings.SERVICE_NAMES_TO_EXCLUDE:
        if pattern in service_name:
            return True
    return False


def incident_data(incident):
    return {'id': incident['id'],
            'title': incident['title'],
            'urgency': incident['urgency'],
            'escalation_policy': incident['escalation_policy']['summary'],
            'service': incident['service']['summary']}


def time_data(incident):
    log_entries = get_log_entries(incident)
    # put date in format athena can inteterpet
    created_at = pagerduty_datetime(incident['created_at'])
    # JSON SerDE wants timestamp to be yyyy-mm-dd hh:mm:ss[.fffffffff]
    created_at_formatted = created_at.strftime('%Y-%m-%d %H:%M:%S')
    acknowledgement_time = first_timestamp_for_type(log_entries, 'acknowledge_log_entry')
    resolution_time = first_timestamp_for_type(log_entries, 'resolve_log_entry')
    time_to_acknowledge = seconds_since_occurred(created_at, acknowledgement_time)
    time_to_resolve = seconds_since_occurred(created_at, resolution_time)
    return {'created_at': created_at_formatted,
            'time_to_acknowledge': time_to_acknowledge,
            'time_to_resolve': time_to_resolve}


def user_data(incident):
    log_entries = get_log_entries(incident)
    users_acked = [log['agent']['summary'] for log in log_entries if log['type'] == 'acknowledge_log_entry']
    users_notified = [log['user']['summary'] for log in log_entries if log['type'] == 'notify_log_entry']
    num_acknowledgments = len(users_acked)
    # use set to dedupe so we get a count of unique users notified instead of number of notifications sent
    num_users_notified = len(set(users_notified))
    # notes are in descending chronological order, so first user in the list was the last to be notified
    user_credited = user_credited_for_incident(users_acked, users_notified)
    out_of_hours = incident_was_out_of_hours(user_credited, incident)
    return {'num_acknowledgments': num_acknowledgments,
            'num_users_notified': num_users_notified,
            'user': user_credited,
            'out_of_hours': out_of_hours}

def generate_report(since, until):
    incidents = get_incidents(since, until)
    rows = []
    for incident in incidents:
        row = {}
        if service_is_excluded(incident):
            continue
        if incident['urgency'] == 'low' and settings.EXCLUDE_LOW_URGENCY:
            continue
        row.update(incident_data(incident))
        row.update(time_data(incident))
        row.update(user_data(incident))
        rows.append(row)
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
    pypd.api_key = settings.API_KEY
    since, until = timerange_for_report()
    output_path = '/tmp/%s.json' % since
    rows = generate_report(since, until)
    write_report(rows, output_path)
    upload_report(output_path)


if __name__ == '__main__':
    lambda_handler(None, None)
