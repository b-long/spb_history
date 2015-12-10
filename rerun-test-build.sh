#!/usr/bin/env bash

echo "Sourcing virtual environment"
source env/bin/activate

echo "Re-running build"
python -m rerun_build 1343 https://tracker.bioconductor.org/file6714/spbtest_0.99.1.tar.gz

echo "Build has been submitted."
