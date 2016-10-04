#!/bin/bash

. env/bin/activate

nohup python track_build_completion.py > track_build_completion.log 2>&1 &
nohup python pinger.py > pinger.log 2>&1 & 

