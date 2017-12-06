# TMUX Layout
# +---+---+
# |   |   | 0=controller
# | 0 | 2 | 1=scenario
# |   +---+ 2=info
# +---+   + 3=mininet
# |   | 3 | 4=watch
# | 1 +---+
# |   | 4 |
# +---+---+

SESSION="sdn"
PANE_CONTROLLER=0
PANE_SCENARIO=1
PANE_INFO=2
PANE_MININET=3

# log to stdout
function log
{
	printf '\033[1;33m%s\033[0m\n' "$@"
}

function wait_condition
{
    #$1: condition
    #$2: timeout

    pidFile=$(mktemp)
    touch $pidFile
    until $1; do sleep 0.1; done && rm $pidFile &
    pid=$!
    ( sleep $2; if [[ -e $pidFile ]]; then rm $pidFile; kill $pid; fi; ) &

    wait $pid
}

function process_exists
{
    (($(pgrep $1 | awk '{print $2}' | wc -l)!=0))
}

function file_exists
{
    [ -f "$1" ]
}

function port_exists
{
    nc -z $1 $2
}
