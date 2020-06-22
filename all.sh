#!/bin/bash

source env/bin/activate

killall python3

./run-django.sh
./run-archiver.sh
./run-track_build_completion.sh
./otherscripts.sh

