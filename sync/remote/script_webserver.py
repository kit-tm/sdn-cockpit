# -*- coding: UTF-8 -*-
# 
# This script will start a webserver to display the flow table of switch s1 and s2
# The switches are currently hard-coded (for demo purposes), feel free to change the
# configuration if necessary (SUPERVISE_SWITCHES parameter).
import os, subprocess
from flask import Flask, render_template 
app = Flask(__name__)

SUPERVISE_SWITCHES = ['s1', 's2']

@app.route('/')   # URL '/' to be handled by main() route handler
def main():
    return render_template('main.html')


class Switch():
    def __init__(self, id):
        self.id = id
        self.flows = []

class Flow():
    def __init__(self, id, **kwargs):
        self.id = id
        self.table = kwargs.get('table')
        self.duration = kwargs.get('duration')
        self.n_packets = kwargs.get('n_packets')
        self.priority = kwargs.get('priority')
        self.idle_timeout = kwargs.get('idle_timeout', 'NA')
        self.hard_timeout = kwargs.get('hard_timeout', 'NA')
        # matches
        self.in_port = kwargs.get('in_port', '*')
        self.dl_dst = kwargs.get('dl_dst', '*')
        self.dl_src = kwargs.get('dl_src', '*')
        self.nw_dst = kwargs.get('nw_dst', '*')
        self.nw_src = kwargs.get('nw_src', '*')
        self.tp_src = kwargs.get('tp_src', '*')
        self.tp_dst = kwargs.get('tp_dst', '*')
        # action
        self.actions = kwargs.get('actions', 'DROP')

@app.route('/flowtable')  # URL with a variable
def get_flowtable():    # The function shall take the URL variable as parameter
    switches = []
    for s in SUPERVISE_SWITCHES:
        switch = Switch(s)
        cnt = 0
        for data in poll_switch(s):
            print(data)
            switch.flows.append(Flow(cnt, **data))
            cnt += 1
        switches.append(switch)

    return render_template('flowtable.html', switches=switches)


FLOW_CMD = "sudo ovs-ofctl dump-flows %s -O OpenFlow13 | grep -v OFPST | sed \"s/actions/,actions/\" " \
           "| sed \"s/,output:/;/g\" | sed -r \"s/(duration=[0-9]*)\.[0-9]*s/\\1s/\""
SHOW_FIELDS_JOINED = ["cookie", ("table", "tab"), ("duration", "dur"), ("n_packets", "n"),
                      ("priority", "prio"), ("in_port", "in"), "dl_dst", "dl_src",
                      "nw_dst", "nw_src", "tp_src", "tp_dst", "arp_tpa", "other", 
                      "nw_tos", "actions", "idle_timeout", "hard_timeout"]             
SHOW_FIELDS = map(lambda x: x if not isinstance(x, tuple) else x[0], SHOW_FIELDS_JOINED)
IGNORED_FIELDS = []

def poll_switch(switch):
    cmd = (FLOW_CMD % switch)
    proc = subprocess.Popen(["/bin/bash", "-c", cmd], stdout=subprocess.PIPE)
    lines = proc.stdout.read().split("\n")
    if lines[-1] == "":
        lines.pop()
    arr_dic = map(parse_line, lines)
    return arr_dic

def parse_line(line):
    no_white = line.replace(" ", "")
    field_strs = no_white.split(",")
    key_val = map(lambda kv: kv.split("="), field_strs)
    dic = {}
    for kv in key_val:
        key = kv[0]
        if len(kv) == 2:
            val = kv[1]
        else:
            val = key
            key = "other"
            if key not in dic:
                dic[key] = []
            val = dic[key] + [val]
        dic[key] = val

        if key not in SHOW_FIELDS:
            global IGNORED_FIELDS
            if key not in IGNORED_FIELDS:
                IGNORED_FIELDS += [key]
    return dic

if __name__ == '__main__':  # Script executed directly?
    app.run(host='0.0.0.0',port='3000', debug=True)  # Launch built-in web server and run this Flask webapp