#!/usr/bin/env python3
from datetime import datetime, timezone
import asyncio
import csv
import os
import glob

import boto3
import aiohttp

import settings

BASE_URL = "https://api.pingdom.com/api/3.1"


async def get_checks(session):
    url = f"{BASE_URL}/checks?include_tags=true"
    resp = await session.get(url)
    resp.raise_for_status()
    checks = await resp.json()
    return checks["checks"]


async def get_outages(session, check_id):
    from_ = int(settings.START_DATE.timestamp())
    to_ = int(settings.END_DATE.timestamp())
    url = f"{BASE_URL}/summary.outage/{check_id}/?from={from_}&to={to_}"
    resp = await session.get(url)
    # print(resp.headers)
    if resp.status >= 400:
        # print(await respt.read())
        resp.raise_for_status()

    states = (await resp.json())["summary"]["states"]
    return states


def upload_report(output_path):
    s3_name = "%s%s" % (settings.S3_PREFIX, os.path.basename(output_path))
    s3 = boto3.client("s3")
    s3.upload_file(output_path, settings.S3_BUCKET, s3_name)


class DatedCSVWriter:
    def __init__(self, base_path, fieldnames=None):
        self.base_path = base_path
        self.fieldnames = fieldnames
        self._writers = {}

    def __getitem__(self, pos):
        if pos in self._writers:
            return self._writers[pos]

        output_path = f"{self.base_path}/{pos}.csv"
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
        fp = open(output_path, "w")
        writer = csv.DictWriter(fp, fieldnames=self.fieldnames)
        self._writers[pos] = writer
        writer.writeheader()
        return writer


async def write_report(output_path):
    headers = {"Authorization": f"Bearer {settings.API_KEY}"}
    fieldnames = ["check_id", "service", "timefrom", "timeto", "status", "tags"]
    writer = DatedCSVWriter(output_path, fieldnames=fieldnames)
    async with aiohttp.ClientSession(headers=headers) as session:
        checks = await get_checks(session)
        tasks = [asyncio.ensure_future(get_outages(session, c["id"])) for c in checks]
        pending = tasks[:]
        active = []
        while pending:
            while len(active) > 10:
                done, _ = await asyncio.wait(
                    active, return_when=asyncio.FIRST_COMPLETED
                )
                for d in done:
                    active.remove(d)
            active.append(pending.pop())
        await asyncio.wait(active)
        for c, t in zip(checks, tasks):
            states = t.result()
            for s in states:
                s["service"] = c["name"]
                s["check_id"] = c["id"]
                s["tags"] = ",".join(tag["name"] for tag in c["tags"])
                day = datetime.fromtimestamp(s["timefrom"], timezone.utc).strftime(
                    "%Y-%m-%d"
                )
                writer[day].writerow(s)


async def main():
    await write_report(settings.OUTPUT_PATH)
    for f in glob.glob(f"{settings.OUTPUT_PATH}/*.csv"):
        upload_report(f)


def lambda_handler(event, context):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
