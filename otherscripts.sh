#!/bin/bash

source env/bin/activate

nohup python -m pinger.py >> pinger.log 2>&1 &
