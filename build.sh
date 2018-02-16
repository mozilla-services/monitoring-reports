#!/bin/bash
set -e

if [[ -f lambda.zip ]]; then
    rm lambda.zip
fi

if [[ -d lambda ]]; then
    rm -r lambda
fi

mkdir lambda
pip3 install -r requirements.txt -t lambda/
cp incident_report.py settings.py lambda/

cd lambda
zip -r9 ../lambda.zip .
