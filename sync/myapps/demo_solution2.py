#tm task=demoAlumni

from utils import Rule, send_rule, send_packet, get_port_by_ip

class Application():

    def __init__(self):
        print("+++++++++ Reactive Solution")

    # new switch
    def on_connect(self, switch):
        print("\n>> switch connected", switch.id)

    # packet in
    def on_packet_in(self, packet, switch, inport ):
        print("\n>> ", inport, "switch", switch.id, packet)
        # the magic oracle function knows what to do with the packet...
        use_port = get_port_by_ip(switch, packet.ip_dst)
        if use_port >= 0:
            r = Rule()
            r.MATCH('IP_DST', packet.ip_dst)
            r.ACTION('OUTPUT', use_port)
            send_rule(r, switch)
            # important to not loose any packets!
            send_packet(packet, switch, use_port)
