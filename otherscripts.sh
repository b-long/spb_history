#!/bin/bash

. env/bin/activate

nohup python pinger.py > pinger.log 2>&1 & 

