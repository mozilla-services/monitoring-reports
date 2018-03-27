#!/bin/bash
set -e
set -x

REPORT=$1
CODE="${REPORT}/${REPORT}_report.py"
WORKDIR="${REPORT}-lambda"
ARTIFACT="${REPORT}-lambda.zip"

if [[ ! -f $CODE ]]; then
    echo Cannot find $CODE
    exit 1
fi

if [[ -f $ARTIFACT ]]; then
    rm $ARTIFACT
fi

if [[ -d $WORKDIR ]]; then
    rm -r $WORKDIR
fi

mkdir $WORKDIR

PIP_CMD="pip3 install -r $REPORT/requirements.txt -t $WORKDIR/"

if command -v pip3 >/dev/null; then
    $PIP_CMD
elif command -v docker >/dev/null; then
    docker run -u $UID -w /root -v $(pwd):/root python:3.6 $PIP_CMD
else
    echo 'You must have either python 3 or docker installed to build'
    exit 1
fi

cp $CODE $REPORT/settings.py $WORKDIR/

cd $WORKDIR
zip -r9 ../$ARTIFACT .
