#!/usr/bin/env bash

#!/usr/bin/env bash

# TODO: Switch to common error handler
err_handler() {
    echo "Error on line $1"
}

trap 'err_handler $LINENO' ERR

# Fail fast (err_handler above will be invoked)
# Exit immediately if a command exits with a non-zero status.
set -o errexit
# Treat unset variables as an error when substituting.
set -o nounset

# cd to the scripts current directory
cd -P -- "$(dirname -- "$0")"

echo "Now starting Django ..."
python -m manage runserver 0.0.0.0:8000 >> django.log 2>&1 &
echo "Django.py is running."
echo "The log is available at '$(pwd)/django.log'"
