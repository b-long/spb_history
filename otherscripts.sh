#!/bin/bash

source env/bin/activate

nohup python3 -m pinger.py >> pinger.log 2>&1 &
