#!/bin/bash

source env/bin/activate

killall python

./run-django.sh
./run-archiver.sh
./otherscripts.sh

