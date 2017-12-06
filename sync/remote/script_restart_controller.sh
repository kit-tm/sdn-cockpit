#!/bin/bash

# This script restarts the controller within  the tmux session
# Works if the user is currently attached to the session

# see ../run.sh for the TMUX Layout

source lib.sh

APP=$2

if [ "$1" = true ]; then
    log " + stop currently running controller"
    # try it the nice way first
    tmux send-keys -t $SESSION.$PANE_CONTROLLER C-c
    sleep 0.1 #TODO higher grace period?
    # but either way, make sure it is really killed...
    ps -ef | grep ryu-manager | awk '{print $2}' | sudo xargs kill -9
    sleep 0.2 #TODO unnecessary?

    log " + delete all flows"
    tmux send-keys -t $SESSION.$PANE_MININET ENTER ENTER 'dpctl del-flows' ENTER
    sleep 0.2 #TODO unnecessary? (if dpctl del-flows blocks)

    log " + restart controller"
else
    log " + start controller"
fi

tmux send-keys -t $SESSION.$PANE_CONTROLLER 'python -m py_compile '$APP' && ryu-manager --use-stderr --nouse-syslog --log-conf "" '$APP C-m
log " + waiting for controller to start"
wait_condition "port_exists localhost 6633" 5
status=$?
if (( status!=0 )); then
    log " + timed out"
fi

exit $status
