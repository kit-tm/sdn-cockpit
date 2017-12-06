#!/bin/bash

# This script restarts the controller within  the tmux session
# Works if the user is currently attached to the session

# see ../run.sh for the TMUX Layout

source lib.sh

SCENARIO=$2

if [ "$1" = true ]; then
    log " + stop mininet"
    ps -ef | grep script_run_mininet.py | awk '{print $2}' | sudo xargs kill -9
    tmux send-keys -t $SESSION.$PANE_MININET C-c
    tmux send-keys -t $SESSION.$PANE_MININET "clear" C-m

    log " + restart mininet"
else
    log " + start mininet"
fi

rm __mn_ready
tmux send-keys -t $SESSION.$PANE_MININET "sudo python remote/script_run_mininet.py "$SCENARIO C-m
log " + waiting for mininet to start"
wait_condition "file_exists __mn_ready" 10
status=$?
if (( status!=0 )); then
    log " + timed out"
fi

exit $status
