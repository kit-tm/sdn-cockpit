# You can select your task through this when implementing
# subsequent tasks

#tm task=demo

from controller import SDNApplication

# Basic imports for Ryu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6

from netaddr import IPAddress, IPNetwork

# This is the demo application
#
# We assume the following association beween ports and
# connected ASes
#
# Port : AS
#    1 : AS1 (17.0.0.0/8)
#    2 : AS2022
#    3 : AS16
#    4 : AS144

class DemoApplication(SDNApplication):
    """ A demonstration of a basic controller application

        Helper functions are provided by the super class
        SDNApplication (which can be found in controller.py)
    """
    def __init__(self, *args, **kwargs):
        super(DemoApplication, self).__init__(*args, **kwargs)
        self.info("Demo Application")

        # The total_packets variable keeps track of the
        # number of packets that have been forwarded to the
        # controller.
        self.total_packets = 0
        self.packets_by_ip = dict()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """ This method is invoked when a packet does not match any
            of the rules deployed on a switch. The controller can
            take subsequent action to update the switch flowtable entries
            and handle the packet itself.
        """
        # The message that the switch sent to the controller
        msg = ev.msg
        # The datapath over which the message was received
        datapath = msg.datapath
        # The actual packet contents, which are encapsulated in the
        # OpenFlow message.
        data = msg.data
        # The OpenFlow protocol used between the switches and the
        # controllers
        ofproto = datapath.ofproto

        # Information on the port, over which the packet was received
        # by the switch. This will come in handy later on ...
        in_port = msg.match["in_port"]

        # Parses the packet data, so we can easily handle it as an
        # object inside the controller
        pkt = packet.Packet(data)

        # Retreive the Ethernet-part of the packet
        # We do this, because we want to handle ARP packets in a
        # special way.
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            # This is an ARP packet. It must be handled differently
            # ensure direct connectivity between edge nodes of the ASes
            self.handle_arp(datapath, in_port, eth, data)
            return

        # Retreive the IPv4-part of the packet
        ip = pkt.get_protocol(ipv4.ipv4)

        if ip is None:
            # This is not an IPv4 packet. Discard it silently.
            return

        if self.protect_our_network(datapath, in_port, ip.src, ip.dst):
            return

        self.total_packets += 1

        # A range of IP addresses that are handled by this AS
        our_address_range = IPNetwork("17.0.0.0/8")

        traffic_type = ""

        if IPAddress(ip.dst) in our_address_range and in_port != 1:
            traffic_type = "ingress"

            # Flood the message on all ports.
            self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)
        elif IPAddress(ip.src) in our_address_range and in_port == 1:
            traffic_type = "egress"

            # Flood the message on all ports.
            self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)
        else:
            # This is most likely transit traffic. And since we are
            # not the salvation army we dispose of it quietly.
            traffic_type = "transit"

        print(".. total messages received: {:d} ({:s} traffic)".format(
            self.total_packets, traffic_type
        ))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ This method would provide an appropriate hook, if we
            wanted to do anything in advance of processing individual
            packets.
        """
        pass

    def protect_our_network(self, datapath, in_port, src_ip, dst_ip):
        """ Count IP source addresses and launch contermeasures
            to protect the controller and prevent it from being flooded
            with packet_in messages.
        """
        if not src_ip in self.packets_by_ip:
            self.packets_by_ip[src_ip] = 0

        self.packets_by_ip[src_ip] += 1

        if in_port != 1:
            if self.packets_by_ip[src_ip] == 1000:
                # O.K., we've been playing nice long enough ...
                self.launch_countermeasures(datapath, src_ip)
                return True

            if self.packets_by_ip[src_ip] > 1000:
                # Just some lingering packets that got through before
                # our block rule became effective.
                return True

        # We dont want to talk to spammers.
        if in_port == 1 and self.packets_by_ip.get(dst_ip, 0) > 1000:
            return True

        return False

    def launch_countermeasures(self, datapath, src_ip):
        """ Deploy a block rule based on IP source addresses """
        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = src_ip
        )

        # An empty action list indicates a drop rule
        self.set_flow(datapath, match, [], priority = 2)

        warn  = "   WARNING! Traffic limit exceeded for IP {:s}!".format(src_ip)
        warn += " Dropping packets!"

        print(warn)

    def handle_arp(self, datapath, in_port, eth, data):
        """ This method implements a simple mechanism to install
            forwarding rules for ARP packets. Packets that are
            not handled by any of these rules are flooded to
            nearby switches.
        """
        ofproto = datapath.ofproto

        dst = eth.dst
        src = eth.src

        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_ARP,
            eth_dst = src
        )

        # Progamm a flow that forwards ARP packets to directly connected
        # network nodes so we don't have to bother with subsequent
        # ARP packets anymore.
        self.set_flow(datapath, match, [parser.OFPActionOutput(in_port)],
            priority = 1)

        # Flood the received ARP message on all ports of the switch
        self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)
