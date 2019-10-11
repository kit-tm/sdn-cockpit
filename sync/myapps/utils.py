from netaddr import IPAddress, IPNetwork

# send rule to switch
def send_rule(rule, switch):
    switch.execute_rule(rule)

def is_arp(packet):
    return packet.is_arp

def send_packet(packet, switch, port):
    switch.send_packet(packet, port)

# Helper function used for demo.py
# Some magic oracle knows where the IP addresses are :-) 
def get_port_by_ip(switch, ip):
    if switch.id == 1:
        return 5
    if switch.id == 2:
        for iprange, port in [('20.0.1.0/24', 2), ('20.0.2.0/24', 3), ('20.0.3.0/24', 4), ('20.0.4.0/24', 5)]:
            address_range = IPNetwork(iprange)
            if IPAddress(ip) in address_range:
                return port
        return -1

class Rule():

    def __init__(self):
        self.matches = {}
        self.actions = {}
        self.table = 0
        self.prio = 100

    # add a match
    def MATCH(self, key, value=''):
        self.matches[key] = value

    # add an action
    def ACTION(self, key, value=''):
        self.actions[key] = value

    # set the flow table
    def TABLE(self, table):
        self.table = table

    # set priority
    def PRIORITY(self, prio):
        self.prio = prio



