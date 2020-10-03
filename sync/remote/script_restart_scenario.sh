#!/bin/bash

# This script restarts the controller within  the tmux session
# Works if the user is currently attached to the session

# see ../run.sh for the TMUX Layout

source lib.sh

SCENARIO=$2
TASK=$3

if [ "$1" = true ]; then
    log " + stop currently running scenario"
    tmux send-keys -t $SESSION.$PANE_SCENARIO C-c
    sleep 0.2 #TODO higher grace period?
    ps -ef | grep "sudo python3 remote/proxy.py" | awk '{print $2}' | sudo xargs kill -9
    tmux send-keys -t $SESSION.$PANE_SCENARIO "clear" C-m
    sleep 0.2 #TODO unnecessary?

    log " + restart scenario"
else
    log " + start scenario"
fi

tmux send-keys -t $SESSION.$PANE_SCENARIO "sudo python3 remote/proxy.py "$SCENARIO" "$TASK C-m
