#!/bin/bash

# This script restarts the controller within  the tmux session
# Works if the user is currently attached to the session

# see ../run.sh for the TMUX Layout

source lib.sh

log " + kill all"
# kill controller
ps -ef | grep ryu-manager | awk '{print $2}' | sudo xargs kill -9
# kill mininet
ps -ef | grep script_run_mininet.py | awk '{print $2}' | sudo xargs kill -9
# kill remaining instances of trafgen
ps -ef | grep trafgen | awk '{print $2}' | sudo xargs kill -9

#ps -ef | grep script_run_mininet.py | awk '{print $2}' | sudo xargs kill -9
tmux send-keys -t $SESSION.$PANE_MININET "sudo mn --clean" C-m
