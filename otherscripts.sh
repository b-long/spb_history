#!/usr/bin/env bash

echo "Enabling virtual environment"
source env/bin/activate

echo "starting pinger"
##nohup python3 -m pinger.py >> pinger.log 2>&1 &
python3 -m pinger.py >> pinger.log 2>&1 &
