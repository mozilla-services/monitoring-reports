#!/bin/bash
set -e

if [[ -f lambda.zip ]]; then
    rm lambda.zip
fi

if [[ -d lambda ]]; then
    rm -r lambda
fi

mkdir lambda

PIP_CMD='pip3 install -r requirements.txt -t lambda/'

if command -v pip3 >/dev/null; then
    $PIP_CMD
elif command -v docker >/dev/null; then
    docker run -w /root -v $(pwd):/root python:3.6 $PIP_CMD
else
    echo 'You must have either python 3 or docker installed to build'
    exit 1
fi

cp incident_report.py settings.py lambda/

cd lambda
zip -r9 ../lambda.zip .
