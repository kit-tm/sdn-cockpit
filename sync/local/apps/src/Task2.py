from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6, tcp

from cockpit import CockpitApp
from netaddr import IPAddress, IPNetwork

from collections import namedtuple

#tm task=learning2

ETHERTYPES = {2048: "IPv4", 2054: "ARP"}
L4PROTO = {1: "ICMP", 4: "IP-in-IP", 6: "TCP", 17: "UDP"}

## Clear ARP cache
##  --> h1 ip -s -s neigh flush all  


## TODO 0: use this class to store a dataset per host connected to the network
HostInfo = namedtuple("HostInfo", ["ip", "mac", "dp", "port"])
#  Example:
#    hostX = HostInfo("127.0.0.1", "00:00:00:00:00:01", dp, 99)
#    print("IP: {}, MAC: {}".format(hostX.ip, hostX.mac))

class LearningSwitch(CockpitApp):
    ## Initialize SDN-App
    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)
        self.hosts = {}
        self.pkt_count = {}


    ## Creates an ARP-REPLY packet
    def create_arp_reply(self, src_mac, src_ip, dst_mac, dst_ip):
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,
                                           dst=dst_mac,
                                           src=src_mac))
                                           
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=src_mac,
                                 src_ip=src_ip,
                                 dst_mac=dst_mac,
                                 dst_ip=dst_ip))
                                 
        return pkt
         
         
    def debug_output(self, dp, pkt, in_port):
        eth = pkt.get_protocol(ethernet.ethernet)
        
        self.pkt_count[dp.id] += 1
        
        ## TODO 1: Enable some more logging?
        ## Info: Packet-in / Ethernet packet
        print("/// [Switch {}]: PACKET-IN (#{}) on port: {}".format(dp.id, self.pkt_count[dp.id], in_port))
        print("      SRC: {}, DST: {} --> {}".format(eth.src, eth.dst, ETHERTYPES[eth.ethertype]))
        
#        ## Info: IP Packet
#        if eth.ethertype == ether_types.ETH_TYPE_IP:
#            ip_pkt = pkt.get_protocol(ipv4.ipv4)
#            print("           {:17},      {:17} --> {}".format(ip_pkt.src, ip_pkt.dst, L4PROTO[ip_pkt.proto]))
#            
#            ## Info: TCP Packet
##            if ip_pkt.proto == 6:
##                tcp_pkt = pkt.get_protocol(tcp.tcp)
##                print("      SRC-PORT: {}, DST-PORT: {}, SEQ: {}, ACK: {}".format(tcp_pkt.src_port, tcp_pkt.dst_port, tcp_pkt.seq, tcp_pkt.ack))
#
#        if eth.ethertype == ether_types.ETH_TYPE_ARP:
#            arp_pkt = pkt.get_protocol(arp.arp)
#            print("  [ARP] SRC-MAC: {}, SRC-IP: {}; DST-MAC: {} DST-IP: {}".format(arp_pkt.src_mac, arp_pkt.src_ip, arp_pkt.dst_mac, arp_pkt.dst_ip))
        
#       # --> see https://osrg.github.io/ryu-book/en/html/packet_lib.html for more info


    ## When a new switch connects to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath

        ## init (per-data path) variables
        self.pkt_count[dp.id] = 0

        ## some debug output        
        print("")
        print("")
        print("/// Switch connected. ID: {}".format(dp.id))
        
        ## default "all to controller" flow
        match = parser.OFPMatch()
        action = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.program_flow(dp, match, action, priority=0, idle_timeout=0, hard_timeout=0)
        
        ## --> see https://osrg.github.io/ryu-book/en/html/openflow_protocol.html for more match options,


    ## When a new packet comes in at the controller -- "PACKET-IN"
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # all info is stored in the ev object, extract some relevant fields
        msg = ev.msg
        dp = msg.datapath
        in_port = msg.match["in_port"]
        data = msg.data
        pkt = packet.Packet(data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # ignore LLDP Packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        self.debug_output(dp, pkt, in_port)

        ## TODO 2: use ARP packets to learn about hosts
        ## TODO 3: answer ARP requests, DO NOT forward or even broadcast them!
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            print("  --> TODO handle ARP")
            
        elif eth.ethertype == ether_types.ETH_TYPE_IP:
            ## TODO 4: Flood packets? Bad idea! Can't we reuse something for the learning switch task?
            ## TODO 5: Some subtle details to keep in mind, if multiple SDN-switchs are in use.

            self.send_pkt(dp, data, port = ofproto.OFPP_FLOOD)
        else:
            print("  --> DROP PACKET")

