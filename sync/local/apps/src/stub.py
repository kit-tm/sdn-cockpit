from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6

from cockpit import CockpitApp
from netaddr import IPAddress, IPNetwork

# Select your task by setting this variable
#tm task=demo

class StubApp(CockpitApp):

    def __init__(self, *args, **kwargs):
        super(StubApp, self).__init__(*args, **kwargs)
        self.info('StubApp')

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ This method would provide an appropriate hook, if we
            wanted to do anything in advance of processing individual
            packets.
        """
        pass

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """ This method is invoked when a packet does not match any
            of the rules deployed on a switch. The controller can
            take subsequent action to update the switch flowtable entries
            and handle the packet itself.
        """
        pass
