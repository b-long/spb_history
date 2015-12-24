#!/usr/bin/env bash

error() {
  local parent_lineno="$1"
  local message="$2"
  local code="${3:-1}"
  if [[ -n "$message" ]] ; then
    echo "Error on or near line ${parent_lineno}: ${message}; exiting with status ${code}"
  else
    echo "Error on or near line ${parent_lineno}; exiting with status ${code}"
  fi
  exit "${code}"
}
trap 'error ${LINENO}' ERR


# cd to the scripts current directory
cd -P -- "$(dirname -- $0)" || $(echo "Error finding run directory." && exit 1)
dir=$(dirname -- "$0")
# Default executing user (this feature not used)
user=""
name=$(basename "$0")

# Basic command representing this service
cmd="python -m track_build_completion"
# As a workaround to https://github.com/pypa/virtualenv/issues/150 , we should 
# activate the virtual environment before setting "nounset"

# Fail fast (err_handler above will be invoked)
# Exit immediately if a command exits with a non-zero status.
set -o errexit

# Variables that depend on the name of this executable
pid_file=name.pid
stdout_log="$name.log"
stderr_log="$name.err"

print_usage() {
  echo "Usage: $0 {start|stop|restart|status}"
  exit 1
}

if [ -z "$1" ]; then
  print_usage
fi

get_pid() {
  cat "$pid_file"
}

is_running() {
  [ -f "$pid_file" ] && ps "$(get_pid)" > /dev/null 2>&1
}

do_startup() {
  echo "Attempting startup sequence"
  cd "$dir" || $(echo "Error finding run directory." && exit 1)
  
  source env/bin/activate
  echo "Virtual environment activated"
  if [ -z "$user" ]; then
    echo "Starting $name as current user."
    # shellcheck disable=SC2024
    nohup "$($cmd)" >> "$stdout_log" 2>> "$stderr_log" &
  else
    echo "Starting $name as super user"
    # shellcheck disable=SC2024
    sudo -u "$user" "$($cmd)" >> "$stdout_log" 2>> "$stderr_log" &
  fi
  echo $! > "$pid_file"
  if ! is_running; then
      echo "Unable to start, see $stdout_log and $stderr_log"
      exit 1
  fi
}

case "$1" in
    start)
    if is_running; then
        echo "Already started"
    else
        do_startup
    fi
    ;;
    stop)
    if is_running; then
        echo -n "Stopping $name.."
        kill "$(get_pid)"
        for i in {1..10}
        do
            if ! is_running; then
                break
            fi

            echo -n "."
            sleep 1
        done
        echo

        if is_running; then
            echo "Not stopped; may still be shutting down or shutdown may have failed"
            exit 1
        else
            echo "$name is stopped."
            if [ -f "$pid_file" ]; then
                rm "$pid_file"
            fi
        fi
    else
        echo "Not running"
    fi
    ;;
    restart)
    $0 stop
    if is_running; then
        echo "Unable to stop, will not attempt to start"
        exit 1
    fi
    $0 start
    ;;
    status)
    if is_running; then
        echo "Running"
    else
        echo "$name is stopped."
        exit 1
    fi
    ;;
    *)
    print_usage
    ;;
esac

exit 0

# echo "Now starting track_build_completion.py ..."
# nohup python -m track_build_completion > track_build_completion.log 2>&1 &
# tracker_pid=$!
# echo "$tracker_pid" > pid_file
# echo "track_build_completion.py is running."
# echo "The log is available at '$(pwd)/track_build_completion.log'"
