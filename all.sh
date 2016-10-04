#!/bin/bash

source env/bin/activate

killall python

./run-django.sh
./run-archiver.sh
./run-track_build_completion.sh
./otherscripts.sh

