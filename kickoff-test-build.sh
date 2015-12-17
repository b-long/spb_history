#!/usr/bin/env bash

# TODO: Switch to common error handler
err_handler() {
    echo "Error on line $1"
}

trap 'err_handler $LINENO' ERR

# cd to the scripts current directory
cd -P -- "$(dirname -- "$0")"

# As a workaround to https://github.com/pypa/virtualenv/issues/150 , we should 
# enable the virtual environment before setting "nounset"
echo "Enabling virtual environment"
source env/bin/activate

# Fail fast (err_handler above will be invoked)
# Exit immediately if a command exits with a non-zero status.
set -o errexit
# Treat unset variables as an error when substituting.
set -o nounset

echo "Re-running build"

# Test that previously failed with LaTex issues:
python -m rerun_build 1343 https://tracker.bioconductor.org/file6757/cellTree_0.99.3.tar.gz

# Test that doesn't include LaTex problems:
# python -m rerun_build 1343 https://tracker.bioconductor.org/file6750/spbtest_0.99.2.tar.gz

# Test with LaTex problems, and others:
# python -m rerun_build 1343 https://tracker.bioconductor.org/file6770/globalSeq_0.99.4.tar.gz

echo "Build has been submitted."
