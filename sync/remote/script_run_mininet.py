from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.link import TCLink

from termcolor import colored
import sys
import time
import yaml
import os
from functools import partial

def panic(*msg):
    print ""
    print "    " + colored("*"*20+" ERROR "+"*"*20, "white", "on_red")
    for m in msg:
        print "    " + m
    print "    " + colored("*"*47, "white", "on_red")
    exit(1)

def info(*msg):
    print ""
    print "    " + colored("*"*30, "white", "on_yellow")
    for m in msg:
        print "    " + m
    print "    " + colored("*"*30, "white", "on_yellow")

if len(sys.argv) > 1:
    scenariofile = sys.argv[1]
    resultfile = None
    if len(sys.argv) == 3:
        resultfile = sys.argv[2]

    topology = None
    try:
        with open(scenariofile, "r") as file:
            parsed = yaml.safe_load(file.read())
            topology = parsed.get("root").get("topology")
    except Exception as e:
        panic("Scenario file %s invalid (could not be parsed); %s" % (scenariofile, str(e)))


    switches = topology.get("switches")
    hosts = topology.get("hosts")
    links = topology.get("links")


    # save current topology so that minint is only restarted
    # if the topology is changed
    topologyfile = os.path.join(os.getcwd(), "tmp_topology.mn")
    if os.path.exists(topologyfile):
        os.remove(topologyfile) 
    with open(topologyfile, "w") as file:
        file.write(yaml.dump(topology))

    mn_dpids = 0
    mn_switches = dict()
    mn_hosts = dict()
    mn_objects = dict()

    net = Mininet(link=TCLink, waitConnected=True)

    net.addController('c0', controller=RemoteController, ip='127.0.0.1',
        port=6633)

    # create switches
    for switch in switches:
        if not switch.get("enabled") == False:
            name = switch.get("name")
            s = net.addSwitch(name, dpid=str(switch.get("dpid", mn_dpids)))
            mn_switches[name] = s
            mn_objects[name] = s
            mn_dpids+=1

    # create hosts
    for host in hosts:
        name = host.get("name")
        mn_host = net.addHost(name, ip = host.get("ip"),
            defaultRoute = "dev {:s}-eth0".format(name))
        mn_hosts[name] = mn_host
        mn_objects[name] = mn_host

    # create links
    for link in links:
        if len(link) == 3:
            n1, n2, bandwitdh = link
            net.addLink(mn_objects[n1], mn_objects[n2], bw=bandwitdh)
        elif len(link) == 5:
            n1, p1, n2, p2, bandwitdh = link
            net.addLink(mn_objects[n1], mn_objects[n2], port1=p1, port2=p2,
                bw=bandwitdh)

    """
    # deployment file
    for itemname, item in net.items():
        print item.intfList()
    topologyfile2 = os.path.join(os.getcwd(), "tmp_topology_data.mn")
    if os.path.exists(topologyfile2):
        os.remove(topologyfile2) 
    with open(topologyfile2, "w") as file:
        file.write("sd")
    """

    net.start()
    with open('__mn_ready', 'w'):
        pass
    CLI(net)
    net.stop()
