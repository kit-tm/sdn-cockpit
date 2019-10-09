
# send rule to switch
def send_rule(rule, switch):
    switch.execute_rule(rule)

def is_arp(packet):
    return packet.is_arp

class Rule():

    def __init__(self):
        self.matches = {}
        self.actions = {}
        self.table = 0
        self.prio = 100

    # add a match
    def MATCH(self, key, value):
        self.matches[key] = value

    # add an action
    def ACTION(self, key, value):
        self.actions[key] = value

    # set the flow table
    def TABLE(self, table):
        self.table = table

    # set priority
    def PRIORITY(self, prio):
        self.prio = prio



