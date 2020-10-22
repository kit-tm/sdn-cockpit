#!/bin/bash

# This file should be started inside the virtual machine, i.e., at the
# remote end. As soon as the scripts are running, they will try to contact
# the local end via a REST api (and later on communicate via RPCs).

source lib.sh

DEFAULT_APP="local/apps/src/demo.py"
DEFAULT_SCENARIO="$PWD/local/apps/scenarios/demo.yaml"

#tmux kill-server
log " + cleanup mininet"
sudo mn -c

log " + cleanup proxy tmux session"
tmux list-sessions
tmux kill-session -t $SESSION

log " + cleanup remaining processes"
ps -ef | grep python | awk '{print $2}' | sudo xargs kill -9
ps -ef | grep trafgen | awk '{print $2}' | sudo xargs kill -9

log " + Creating sdn tmux session"
tmux new-session -d -s $SESSION
tmux split-window -h
tmux split-window -v
tmux split-window -v -p 40
tmux select-pane -t 0
tmux split-window -v -p 40

# TMUX Layout
# +---+---+
# |   |   | 0=controller
# | 0 | 2 | 1=proxy
# |   +---+ 2=info
# +---+   + 3=mininet
# |   | 3 | 4=watch
# | 1 +---+
# |   | 4 |
# +---+---+

# sudo /etc/init.d/openvswitch-switch restart

# ps -ef | grep python | awk '{print $2}' | sudo xargs kill -9

remote/script_restart_controller.sh false $DEFAULT_APP
remote/script_restart_task.sh false BootDummy
remote/script_restart_mininet.sh false $DEFAULT_SCENARIO
remote/script_restart_scenario.sh false $DEFAULT_SCENARIO
tmux select-pane -t 4
tmux send-keys "python3 remote/script_run_watch.py" C-m

# preselect mininet pane
tmux select-pane -t $SESSION.$PANE_MININET

# attach
tmux attach-session -t $SESSION
