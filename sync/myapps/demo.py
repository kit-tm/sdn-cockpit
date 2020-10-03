#tm task=demoAlumni

from utils import Rule, send_rule

class Application():

    def __init__(self):
        print("+++++++++ My App")

    # new switch
    def on_connect(self, switch):
        print("switch connected", switch.id)


    # packet in
    def on_packet_in(self, packet, switch, inport ):
        print("inport", inport, "switch", switch.id, packet.IP_SRC, packet.IP_DST)
