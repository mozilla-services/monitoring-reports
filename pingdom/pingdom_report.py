#!/usr/bin/env python3
import asyncio
import csv
import os

import boto3
import aiohttp

import settings

BASE_URL = "https://api.pingdom.com/api/3.1"


async def get_checks(session):
    url = f"{BASE_URL}/checks"
    resp = await session.get(url)
    resp.raise_for_status()
    checks = await resp.json()
    return checks["checks"]


async def get_outages(session, check_id):
    from_ = settings.START_DATE.timestamp()
    while True:
        url = f"{BASE_URL}/summary.outage/{check_id}/?from={from_}"
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


async def write_report(output_path):
    headers = {"Authorization": f"Bearer {settings.API_KEY}"}
    with open(output_path, "w") as csvfile:
        fields = ["check_id", "service", "timefrom", "timeto", "status"]
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        async with aiohttp.ClientSession(headers=headers) as session:
            checks = await get_checks(session)
            tasks = [
                asyncio.ensure_future(get_outages(session, c["id"])) for c in checks
            ]
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
                    writer.writerow(s)


async def main():
    await write_report(settings.OUTPUT_PATH)
    upload_report(settings.OUTPUT_PATH)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
