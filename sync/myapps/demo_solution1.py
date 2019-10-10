#tm task=demoAlumni

from utils import Rule, send_rule

class Application():

    def __init__(self):
        print "+++++++++ Proactive Solution"

    # new switch
    def on_connect(self, switch):  
        print "switch connected", switch.id

        if switch.id == 1:
            r = Rule()
            r.MATCH('IP_DST', '20.0.0.0/16')
            r.ACTION('OUTPUT', 5)
            send_rule(r, switch)

        if switch.id == 2:
            r = Rule()
            r.MATCH('IP_DST', '20.0.1.0/24')
            r.ACTION('OUTPUT', 2)
            send_rule(r, switch)

            r = Rule()
            r.MATCH('IP_DST', '20.0.2.0/24')
            r.ACTION('OUTPUT', 3)
            send_rule(r, switch)

            r = Rule()
            r.MATCH('IP_DST', '20.0.3.0/24')
            r.ACTION('OUTPUT', 4)
            send_rule(r, switch)

            r = Rule()
            r.MATCH('IP_DST', '20.0.4.0/24')
            r.ACTION('OUTPUT', 5)
            send_rule(r, switch)
    # packet in
    def on_packet_in(self, packet, switch, inport ):
        print(inport, "switch", switch.id, packet)

