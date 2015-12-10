#!/usr/bin/env bash

python -m manage runserver 0.0.0.0:8000 >> django.log 2>&1 &
