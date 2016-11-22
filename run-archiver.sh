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

echo "Now starting archiver.py ..."
python -m archiver >> archiver.log 2>&1 &
echo "archiver.py is started."
echo "The log is available at '$(pwd)/archiver.log'"
