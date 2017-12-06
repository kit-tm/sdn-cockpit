#!/bin/bash

# This script restarts the controller within  the tmux session
# Works if the user is currently attached to the session

# see ../run.sh for the TMUX Layout

source lib.sh

TASK=$2
RESULT=$3

if [ "$1" = true ]; then
    tmux send-keys -t $SESSION.$PANE_INFO C-c
    tmux send-keys -t $SESSION.$PANE_INFO "clear" C-m
fi

tmux send-keys -t $SESSION.$PANE_INFO "python remote/script_run_info.py "$TASK" "$RESULT C-m
